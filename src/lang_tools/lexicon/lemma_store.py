"""SQLite-backed read/query store for the whole lexical graph.

The store is the single read layer over lemmas, concepts, senses, and the
decoupled relation edges. It builds **one** engine - an indexed SQLite database -
and serves every query (point lookups, bounded adjacency joins, filtered reads)
with ``SELECT``s, reconstructing the thin pydantic models through the Parquet
codec seam (`lang_tools.lexicon.codec`).

Why SQLite only:
    The full corpus as in-memory pydantic dicts is ~1.9 GB resident, infeasible
    on a small dyno. SQLite point lookups run at ~0 resident (~30 us/lookup), so
    the store keeps a single code path over SQLite for both the tiny sample and
    the full corpus, instead of a resident/SQLite dual mode. The earlier
    dual-mode seam (resident dicts, eager whole-graph hydration, a mode switch)
    is gone.

Data source:
    `from_data_fol` builds the SQLite database from the source-of-truth Parquet
    under ``data/lexicon/`` - the single load path. The full corpus is produced
    by the ingestion phase; for local development the committed JSONL **sample
    seed** under ``data/bootstrap/`` is parquetized into its **own** corpus at
    ``data/bootstrap/lexicon/`` (by the parquetize notebook) so it never collides
    with the real ``data/lexicon/`` build. When no Parquet is present
    `from_data_fol` raises `CorpusNotFoundError`.

    Load is lean by default: the Parquet rows stream straight into SQLite without
    building pydantic models (phase 5.3 showed retaining every model is what drives
    the load's memory peak). The built database is **persisted** beside the corpus
    (``<corpus>/_store.sqlite``, gitignored) and reused while a content signature
    over the Parquet files is unchanged - so a warm load is a bare connect. Pass
    ``validate=True`` for the slower row-validating path, or ``db_path=":memory:"``
    / ``use_cache=False`` to skip the persisted cache.

Back-references:
    The persisted models leave their convenience back-references
    (`sense.lemma`, `lemma.senses`, `concept.lemmas`, ...) empty. They are filled
    **on demand**, per call, by the ``hydrate_*`` methods (a bounded 1-2 hop
    SQLite read), not eagerly across the whole graph. Hydrated instances are
    fresh per call - there is no shared-instance identity. An un-hydrated
    back-reference read through ``resolve_*`` raises `NotHydratedError`.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.language.normalization import has_accent
from lang_tools.language.normalization import normalize as _normalize
from lang_tools.lexicon.card import CardQuery
from lang_tools.lexicon.card import LemmaCard
from lang_tools.lexicon.codec import _COLUMNS
from lang_tools.lexicon.codec import LEXICON_SUBDIR
from lang_tools.lexicon.codec import _load_table
from lang_tools.lexicon.codec import load_raw_table
from lang_tools.lexicon.codec import model_from_row
from lang_tools.lexicon.codec import row_from_model
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.sense import Sense
from lang_tools.params.lang_tools_params import get_lang_tools_params

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Sequence

    from pydantic import BaseModel

    from lang_tools.lexicon.relations import ConceptRelation
    from lang_tools.lexicon.relations import FalseFriendRelation
    from lang_tools.lexicon.relations import SenseRelation

#: Bump to invalidate every persisted SQLite cache after a schema/codec change.
#: v2: concepts gained ``lexfile`` + ``examples`` and hypernym `ConceptRelation`
#: edges are now populated (phase 5.54 / 5.5 Step 4).
#: v3: concepts gained ``commonness`` and senses carry the phase-6 frequency /
#: CEFR values, so a v2 cache is missing columns the queries now select.
#: v4: the ``sense_relations`` table (phase 7), so a v3 cache lacks a table.
#: v5: concepts gained ``topics`` and the derived ``lemma_topics`` table (phase 8).
#: v6: concepts gained ``definition_sources`` (per-gloss provenance, phase 8).
#: v7: the derived ``lemma_drill`` table behind `LemmaCard` (phase 9).
CACHE_VERSION = 7

#: Filename of the persisted SQLite cache built inside a corpus directory. It is
#: rebuilt from the Parquet whenever the corpus signature changes; never committed
#: (the whole ``data/`` tree is gitignored).
STORE_DB_NAME = "_store.sqlite"

# Resolve the circular back-reference annotations (Lemma <-> Sense <-> Concept)
# now that all three classes are importable in this namespace. model_rebuild
# picks the classes up from this module's globals; a TYPE_CHECKING-only import in
# the model modules is not enough for the runtime rebuild.
Sense.model_rebuild()
Concept.model_rebuild()
Lemma.model_rebuild()

#: The lexical tables, in dependency order (lemmas/concepts before the edges).
TABLES: tuple[str, ...] = (
    "lemmas",
    "concepts",
    "senses",
    "false_friends",
    "concept_relations",
    "sense_relations",
)

#: Columns stored as JSON text in SQLite (the list / dict model fields). Every
#: other column binds to a native SQLite value.
_JSON_COLUMNS: dict[str, frozenset[str]] = {
    "lemmas": frozenset({"topics", "examples", "sources"}),
    "concepts": frozenset({"definitions", "examples", "topics", "definition_sources"}),
    "senses": frozenset(),
    "false_friends": frozenset({"explanation_notes"}),
    "concept_relations": frozenset(),
    "sense_relations": frozenset(),
}

#: Secondary indexes per table (beyond the implicit primary key on ``id``).
_INDEXES: dict[str, tuple[str, ...]] = {
    "lemmas": ("language",),
    "concepts": (),
    "senses": ("lemma_id", "concept_id"),
    "false_friends": ("lemma_id_a", "lemma_id_b"),
    "concept_relations": ("concept_id_a", "concept_id_b"),
    "sense_relations": ("sense_id_a", "sense_id_b"),
}

#: Tables whose first column (``id``) is a unique primary key.
_HAS_ID_PK: frozenset[str] = frozenset({"lemmas", "concepts", "senses"})


class CorpusNotFoundError(FileNotFoundError):
    """Raised when no Parquet corpus is present at the expected location."""

    def __init__(self, corpus_dir: Path) -> None:
        """Initialize with the corpus directory that was checked.

        Args:
            corpus_dir: The ``<data_fol>/lexicon`` directory that holds no corpus.
        """
        super().__init__(f"Corpus not found at {corpus_dir}")
        self.corpus_dir = corpus_dir


def _dedupe_by_id(items: list[Concept]) -> list[Concept]:
    """Return concepts unique by id, preserving first-seen order."""
    seen: set[str] = set()
    out: list[Concept] = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            out.append(item)
    return out


def _build_schema(conn: sqlite3.Connection) -> None:
    """Create the table and index schema for every lexical table."""
    for name in TABLES:
        cols = _COLUMNS[name]
        defs = [
            f"{col} TEXT PRIMARY KEY" if (col == "id" and name in _HAS_ID_PK) else col
            for col in cols
        ]
        conn.execute(f"CREATE TABLE {name} ({', '.join(defs)})")
        for col in _INDEXES[name]:
            conn.execute(f"CREATE INDEX idx_{name}_{col} ON {name} ({col})")


def _populate(conn: sqlite3.Connection, tables: dict[str, Sequence[BaseModel]]) -> None:
    """Insert every model into its table, JSON-encoding the nested columns."""
    for name in TABLES:
        cols = _COLUMNS[name]
        json_cols = _JSON_COLUMNS[name]
        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO {name} ({', '.join(cols)}) VALUES ({placeholders})"  # noqa: S608
        rows = []
        for model in tables.get(name, []):
            row = row_from_model(name, model)
            rows.append(
                tuple(
                    json.dumps(row[col], ensure_ascii=False)
                    if col in json_cols
                    else row[col]
                    for col in cols
                ),
            )
        conn.executemany(sql, rows)
    conn.commit()


def _populate_raw(conn: sqlite3.Connection, data_fol: Path) -> list[str]:
    """Stream each table's lean Parquet rows straight into SQLite (no models).

    The fast/lean load path: `codec.load_raw_table` produces rows already in the
    persisted column shape (map columns as dicts, provenance dropped), so each
    column binds directly - JSON columns are dumped, the rest pass through. This
    skips the validate+dump round-trip `_populate` pays. Tables are loaded and
    inserted **one at a time** and freed before the next, so the build's memory
    peak is one table, not the whole corpus.

    Returns:
        The concept ids, for the post-build slug-collision summary.
    """
    concept_ids: list[str] = []
    for name in TABLES:
        cols = _COLUMNS[name]
        json_cols = _JSON_COLUMNS[name]
        placeholders = ", ".join("?" for _ in cols)
        sql = f"INSERT INTO {name} ({', '.join(cols)}) VALUES ({placeholders})"  # noqa: S608
        raw = load_raw_table(name, data_fol=data_fol)
        if name == "concepts":
            concept_ids = [row["id"] for row in raw]
        conn.executemany(
            sql,
            [
                tuple(
                    json.dumps(row.get(col), ensure_ascii=False)
                    if col in json_cols
                    else row.get(col)
                    for col in cols
                )
                for row in raw
            ],
        )
        raw.clear()
    conn.commit()
    return concept_ids


def _derive_lemma_topics(conn: sqlite3.Connection) -> None:
    """Build ``lemma_topics`` and fill each lemma's `topics` from its senses.

    A topic is stored on the concept (a meaning); a lemma's topics are the union
    of its own curated tags and the topics of every concept it has a sense in.
    Deriving them here, once per cache build, keeps them off the persisted lemma
    rows (no second copy to drift) while every read - `get_lemma_by_id`, the
    filters, `lang-tutor`'s selection - sees the full set. The ``lemma_topics``
    table is indexed so a topic filter is a lookup rather than a scan of every
    lemma.
    """
    conn.executescript(
        """
CREATE TABLE lemma_topics AS
  SELECT l.id AS lemma_id, j.value AS topic
    FROM lemmas l, json_each(l.topics) j
  UNION
  SELECT s.lemma_id, j.value
    FROM senses s JOIN concepts c ON c.id = s.concept_id, json_each(c.topics) j;
CREATE INDEX idx_lemma_topics_topic ON lemma_topics (topic);
CREATE INDEX idx_lemma_topics_lemma ON lemma_topics (lemma_id);
UPDATE lemmas SET topics = (
  SELECT json_group_array(topic) FROM (
    SELECT topic FROM lemma_topics t WHERE t.lemma_id = lemmas.id ORDER BY topic
  )
) WHERE id IN (SELECT lemma_id FROM lemma_topics);
""",
    )
    conn.commit()


def _derive_drill_table(conn: sqlite3.Connection) -> None:
    """Build ``lemma_drill``, the narrow indexed table behind `LemmaCard`.

    One row per lemma: its language and part of speech, its **best sense**, and
    the per-text drill filters (character length, single lowercase word, has a
    diacritic). The flags are computed in Python because SQLite's ``lower()``
    is ASCII-only.

    The best sense is the highest ``sense_frequency``; ties go to the more
    common concept (`Concept.commonness`), then the easier CEFR band, then the
    concept id so the pick is deterministic. The commonness tie-break matters
    outside English: the SemCor prior that splits a lemma's frequency across
    its senses is English-only, so every sense of a pt lemma ties on
    frequency, and without it pt ``casa`` would pick "apartment" over "house".

    A card query filters and orders this table alone, then fetches only the
    picked lemma rows, so a random sample over a whole language stays a cheap
    scan. Derived once per cache build, like ``lemma_topics``.
    """
    conn.execute(
        "CREATE TEMP TABLE lemma_flags ("
        "lemma_id TEXT PRIMARY KEY, char_len INTEGER, single_word INTEGER,"
        " accented INTEGER)",
    )
    rows = conn.execute("SELECT id, text FROM lemmas").fetchall()
    conn.executemany(
        "INSERT INTO lemma_flags VALUES (?, ?, ?, ?)",
        [
            (
                row["id"],
                len(row["text"]),
                int(_is_single_word(row["text"])),
                int(has_accent(row["text"])),
            )
            for row in rows
        ],
    )
    conn.executescript(
        """
CREATE TABLE lemma_drill AS
  SELECT l.id AS lemma_id, l.language, l.part_of_speech,
         b.concept_id, b.cefr_level, b.sense_frequency,
         f.char_len, f.single_word, f.accented
    FROM lemmas l
    JOIN temp.lemma_flags f ON f.lemma_id = l.id
    LEFT JOIN (
      SELECT lemma_id, concept_id, cefr_level, sense_frequency FROM (
        SELECT s.lemma_id, s.concept_id, s.cefr_level, s.sense_frequency,
               row_number() OVER (
                 PARTITION BY s.lemma_id
                 ORDER BY s.sense_frequency DESC NULLS LAST,
                          c.commonness DESC NULLS LAST,
                          s.cefr_level ASC NULLS LAST,
                          s.concept_id
               ) AS rank
          FROM senses s JOIN concepts c ON c.id = s.concept_id
      ) WHERE rank = 1
    ) b ON b.lemma_id = l.id;
CREATE UNIQUE INDEX idx_lemma_drill_lemma ON lemma_drill (lemma_id);
CREATE INDEX idx_lemma_drill_level ON lemma_drill (language, cefr_level);
DROP TABLE temp.lemma_flags;
""",
    )
    conn.commit()


def _is_single_word(text: str) -> bool:
    """Return True for one lowercase alphabetic token (no proper nouns)."""
    return text.isalpha() and text == text.lower()


def _card_rank(seed: int, lemma_id: str) -> int:
    """Return a deterministic pseudo-random sort key for a seeded sample."""
    digest = hashlib.blake2b(f"{seed}:{lemma_id}".encode(), digest_size=8).digest()
    return int.from_bytes(digest, "big") >> 1


def _card_where(query: CardQuery) -> tuple[list[str], list[object]]:
    """Return the card SELECT's WHERE clauses and their parameters.

    Every column is read from ``lemma_drill`` (alias ``d``).
    """
    valued: list[tuple[object, str]] = [
        (query.language, "d.language = ?"),
        (query.min_cefr, "d.cefr_level >= ?"),
        (query.max_cefr, "d.cefr_level <= ?"),
        (
            query.topic,
            "d.lemma_id IN (SELECT lemma_id FROM lemma_topics WHERE topic = ?)",
        ),
        (query.part_of_speech, "d.part_of_speech = ?"),
        (query.length, "d.char_len = ?"),
        (query.min_length, "d.char_len >= ?"),
    ]
    clauses = [clause for value, clause in valued if value is not None]
    params: list[object] = [value for value, _ in valued if value is not None]
    if query.accented_only:
        clauses.append("d.accented = 1")
    if query.single_word:
        clauses.append("d.single_word = 1")
    if query.exclude_ids:
        marks = ", ".join("?" for _ in query.exclude_ids)
        clauses.append(f"d.lemma_id NOT IN ({marks})")
        params.extend(query.exclude_ids)
    if query.require_translation:
        for language in query.translation_languages:
            clauses.append(
                "EXISTS (SELECT 1 FROM senses s2"
                " JOIN lemmas l2 ON l2.id = s2.lemma_id"
                " WHERE s2.concept_id = d.concept_id AND l2.language = ?"
                " AND l2.id <> d.lemma_id)",
            )
            params.append(language)
    if query.require_example:
        clauses.append(
            "EXISTS (SELECT 1 FROM concepts c WHERE c.id = d.concept_id"
            " AND json_array_length(c.examples, '$.' || d.language) > 0)",
        )
    return clauses or ["1 = 1"], params


def _new_conn(target: str) -> sqlite3.Connection:
    """Open a SQLite connection with the row factory the store relies on."""
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.create_function("card_rank", 2, _card_rank, deterministic=True)
    return conn


def _corpus_signature(corpus_dir: Path) -> str:
    """Return a content signature over a corpus's Parquet files.

    Hashes the cache version plus each Parquet file's relative path, size, and
    mtime, so a rebuilt or edited corpus busts the persisted SQLite cache while an
    unchanged one reuses it. Uses file stats (not the ``_build.json`` manifest) so
    the seed corpus - which has no manifest - caches too.
    """
    parts = [f"v{CACHE_VERSION}"]
    for path in sorted(corpus_dir.rglob("*.parquet")):
        st = path.stat()
        parts.append(f"{path.relative_to(corpus_dir)}:{st.st_size}:{st.st_mtime_ns}")
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _row_to_model(name: str, row: sqlite3.Row) -> BaseModel:
    """Rebuild a model from a SQLite row, JSON-decoding the nested columns."""
    data = dict(row)
    for col in _JSON_COLUMNS[name]:
        if data.get(col) is not None:
            data[col] = json.loads(data[col])
    return model_from_row(name, data)


def _select_cols(name: str, alias: str | None = None) -> str:
    """Return the comma-joined column list for a table, optionally alias-qualified."""
    prefix = f"{alias}." if alias else ""
    return ", ".join(f"{prefix}{col}" for col in _COLUMNS[name])


class LexiconStore:
    """SQLite-backed read/query store over the whole lexical graph.

    Build it with `from_data_fol` (loads the corpus from disk) or `from_models`
    (in tests / ingestion, from in-memory model lists). Both signatures of the
    query surface match the pre-SQLite store, so callers, the webapp, and
    `lang-tutor` do not change shape.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Wrap an already-built, populated SQLite connection.

        Args:
            conn: A connection whose schema is built and tables populated. Use
                `from_models` / `from_data_fol` rather than calling this directly.
        """
        self._conn = conn

    @classmethod
    def from_models(
        cls,
        *,
        lemmas: list[Lemma],
        concepts: list[Concept],
        senses: list[Sense],
        false_friends: list[FalseFriendRelation],
        concept_relations: list[ConceptRelation],
        sense_relations: list[SenseRelation],
        db_path: Path | None = None,
    ) -> LexiconStore:
        """Build a store by loading model lists into a fresh SQLite database.

        Args:
            lemmas: All lemmas.
            concepts: All concepts.
            senses: All sense edges.
            false_friends: All false-friend edges.
            concept_relations: All concept-relation edges.
            sense_relations: All sense-relation edges.
            db_path: On-disk database path; an in-memory database when None
                (the default - the sample corpus is tiny). The full corpus passes
                a path so the build is paid once.

        Returns:
            The assembled store.
        """
        target = str(db_path) if db_path is not None else ":memory:"
        conn = _new_conn(target)
        _build_schema(conn)
        _populate(
            conn,
            {
                "lemmas": lemmas,
                "concepts": concepts,
                "senses": senses,
                "false_friends": false_friends,
                "concept_relations": concept_relations,
                "sense_relations": sense_relations,
            },
        )
        _derive_lemma_topics(conn)
        _derive_drill_table(conn)
        cls._warn_on_slug_collisions(c.id for c in concepts)
        return cls(conn)

    @classmethod
    def from_data_fol(
        cls,
        data_fol: Path,
        *,
        db_path: Path | str | None = None,
        validate: bool = False,
        use_cache: bool = True,
    ) -> LexiconStore:
        """Build (or reuse) the store from the on-disk Parquet corpus.

        By default this is the fast/lean path: lean Parquet rows are streamed
        straight into SQLite (no pydantic round-trip), and the built database is
        **persisted** to ``<corpus>/_store.sqlite`` and reused on the next load
        while the corpus signature is unchanged - a cache hit is a bare
        ``sqlite3.connect`` (milliseconds, ~no extra memory). A changed corpus
        rebuilds automatically. See phase 5.3 for the profiling behind this.

        Args:
            data_fol: Project data folder; the corpus lives under
                ``<data_fol>/lexicon/``.
            db_path: Explicit SQLite path. ``None`` uses the persisted cache file
                inside the corpus dir; pass ``":memory:"`` for an unpersisted DB.
            validate: When True, take the slower model-validating load path (every
                row parsed through its pydantic model, raising
                `MalformedRecordError` on a bad row) instead of streaming raw rows.
            use_cache: When False, always rebuild and do not read an existing cache.

        Returns:
            The assembled store.

        Raises:
            CorpusNotFoundError: When no Parquet corpus is present.
        """
        corpus_dir = data_fol / LEXICON_SUBDIR
        if not _corpus_present(data_fol):
            raise CorpusNotFoundError(corpus_dir)

        in_memory = db_path is not None and str(db_path) == ":memory:"
        cache_db = (
            None
            if in_memory
            else Path(db_path)
            if db_path is not None
            else corpus_dir / STORE_DB_NAME
        )

        sig = _corpus_signature(corpus_dir) if cache_db is not None else None
        sig_file = (
            cache_db.with_suffix(cache_db.suffix + ".sig")
            if cache_db is not None
            else None
        )
        if (
            use_cache
            and cache_db is not None
            and sig_file is not None
            and cache_db.exists()
            and sig_file.exists()
            and sig_file.read_text(encoding="utf-8") == sig
        ):
            lg.debug("Reusing cached store at {}", cache_db)
            return cls(_new_conn(str(cache_db)))

        if cache_db is not None:  # clear any stale/partial cache before rebuilding
            cache_db.unlink(missing_ok=True)
            if sig_file is not None:
                sig_file.unlink(missing_ok=True)

        if validate:
            store = cls.from_models(**_load_corpus_models(data_fol), db_path=cache_db)
        else:
            conn = _new_conn(str(cache_db) if cache_db is not None else ":memory:")
            _build_schema(conn)
            concept_ids = _populate_raw(conn, data_fol)
            _derive_lemma_topics(conn)
            _derive_drill_table(conn)
            cls._warn_on_slug_collisions(concept_ids)
            store = cls(conn)

        if sig is not None and sig_file is not None:
            sig_file.write_text(sig, encoding="utf-8")
        return store

    @staticmethod
    def _warn_on_slug_collisions(concept_ids: Iterable[str]) -> None:
        """Warn (once, summarized) when concepts share a readable slug.

        Ids stay unique via the ``hash[:12]`` suffix, so a shared slug is only a
        legibility issue - phase 8's dedup pass owns it. Emits a single summary
        line (not one per group: a real corpus has tens of thousands).
        """
        ids_by_slug: dict[str, set[str]] = defaultdict(set)
        for cid in concept_ids:
            # id shape: c__{slug}__{hash[:12]}; the slug is everything between.
            slug = cid[len("c__") : cid.rfind("__")]
            ids_by_slug[slug].add(cid)
        colliding = {slug: ids for slug, ids in ids_by_slug.items() if len(ids) > 1}
        if colliding:
            n_concepts = sum(len(ids) for ids in colliding.values())
            examples = ", ".join(sorted(colliding)[:5])
            lg.warning(
                "Concept slug collisions: {} slug groups span {} concepts "
                "(e.g. {}); ids stay unique via the hash suffix (phase 8 dedup).",
                len(colliding),
                n_concepts,
                examples,
            )

    # --- internal query helpers ------------------------------------------

    def _query(self, name: str, sql: str, params: tuple[object, ...] = ()) -> list:
        """Run a SELECT and rebuild each row into `name`'s model."""
        cur = self._conn.execute(sql, params)
        return [_row_to_model(name, row) for row in cur.fetchall()]

    # --- Lemma reads -----------------------------------------------------

    def get_all_lemmas(self) -> list[Lemma]:
        """Return all lemmas."""
        return self._query("lemmas", f"SELECT {_select_cols('lemmas')} FROM lemmas")  # noqa: S608

    def get_lemma_by_id(self, lemma_id: str) -> Lemma | None:
        """Look up a lemma by its deterministic id (None when absent)."""
        rows = self._query(
            "lemmas",
            f"SELECT {_select_cols('lemmas')} FROM lemmas WHERE id = ?",  # noqa: S608
            (lemma_id,),
        )
        return rows[0] if rows else None

    def get_lemmas_by_language(self, language: str) -> list[Lemma]:
        """Filter lemmas by language code."""
        return self._query(
            "lemmas",
            f"SELECT {_select_cols('lemmas')} FROM lemmas WHERE language = ?",  # noqa: S608
            (language,),
        )

    def get_lemmas_by_topic(self, topic: str) -> list[Lemma]:
        """Filter lemmas carrying a given topic (their own or a sense's concept's)."""
        return self.get_lemmas_filtered(topic=topic)

    def get_lemmas_filtered(
        self,
        language: str | None = None,
        topic: str | None = None,
        *,
        query: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Lemma]:
        """Filter lemmas by language, topic and/or a search prefix, optionally paged.

        A topic matches through the derived ``lemma_topics`` index, so it covers
        both a lemma's own tags and the topics of the concepts it realises.
        A paged read (``limit`` set) is ordered by ``normalized`` then id, so
        consecutive pages neither overlap nor skip; an unpaged read keeps the
        table order.

        Args:
            language: ISO 639-1 code to filter by.
            topic: Topic tag to filter by.
            query: Prefix of the accent- and case-folded form (``normalized``).
            limit: Page size; every match when None.
            offset: Matches to skip before the page (with ``limit``).

        Returns:
            The matching lemmas.
        """
        where, params = self._lemma_filter(language, topic, query)
        sql = f"SELECT {_select_cols('lemmas')} FROM lemmas WHERE {where}"  # noqa: S608
        if limit is not None:
            sql += " ORDER BY normalized, id LIMIT ? OFFSET ?"
            params = (*params, limit, offset)
        return self._query("lemmas", sql, params)

    def count_lemmas_filtered(
        self,
        language: str | None = None,
        topic: str | None = None,
        *,
        query: str | None = None,
    ) -> int:
        """Count the lemmas `get_lemmas_filtered` would return unpaged."""
        where, params = self._lemma_filter(language, topic, query)
        sql = f"SELECT count(*) FROM lemmas WHERE {where}"  # noqa: S608
        return int(self._conn.execute(sql, params).fetchone()[0])

    @staticmethod
    def _lemma_filter(
        language: str | None,
        topic: str | None,
        query: str | None,
    ) -> tuple[str, tuple[object, ...]]:
        """Return the WHERE clause and parameters shared by the lemma filters."""
        clauses = ["1 = 1"]
        params: list[object] = []
        if language:
            clauses.append("language = ?")
            params.append(language)
        if topic:
            clauses.append("id IN (SELECT lemma_id FROM lemma_topics WHERE topic = ?)")
            params.append(topic)
        if query:
            clauses.append("substr(normalized, 1, ?) = ?")
            folded = _normalize(query)
            params.extend([len(folded), folded])
        return " AND ".join(clauses), tuple(params)

    # --- Drill cards -----------------------------------------------------

    def lemma_cards(self, query: CardQuery) -> list[LemmaCard]:
        """Return the drill cards matching a `CardQuery`.

        Each card joins the lemma with its best sense (see `LemmaCard`), the
        sense's concept gloss and examples, and the other lemmas of that concept
        as translations. The match is one indexed SELECT bounded by
        ``query.limit``; the gloss and translations are two batched reads over
        the page.

        Args:
            query: The filters, order, and page size.

        Returns:
            Up to ``query.limit`` cards.
        """
        clauses, params = _card_where(query)
        if query.order == "frequency":
            order = "d.sense_frequency DESC NULLS LAST, d.lemma_id"
        elif query.seed is None:
            order = "random()"
        else:
            order = "card_rank(?, d.lemma_id)"
            params.append(query.seed)
        params.append(query.limit)
        return self._select_cards(
            " AND ".join(clauses),
            tuple(params),
            order=order,
            gloss_language=query.gloss_language,
            translation_languages=query.translation_languages,
        )

    def lemma_card(
        self,
        lemma_id: str,
        *,
        gloss_language: str = "en",
        translation_languages: Sequence[str] = ("en",),
    ) -> LemmaCard | None:
        """Return the drill card of one lemma (None when absent).

        Args:
            lemma_id: The lemma's deterministic id.
            gloss_language: Language of the card's gloss.
            translation_languages: Languages to fill the translations with.

        Returns:
            The card, or None when no lemma has the id.
        """
        cards = self._select_cards(
            "d.lemma_id = ?",
            (lemma_id, 1),
            order="d.lemma_id",
            gloss_language=gloss_language,
            translation_languages=translation_languages,
        )
        return cards[0] if cards else None

    def lemma_sense_cards(
        self,
        lemma_id: str,
        *,
        gloss_language: str = "en",
        translation_languages: Sequence[str] = ("en",),
    ) -> list[LemmaCard]:
        """Return one card per sense of a lemma, best sense first.

        The same shape as `lemma_card`, but for every meaning: each card names
        its sense's concept, band, and frequency, with that concept's gloss,
        translations, and examples. Senses are ordered like the best-sense pick
        (frequency, then commonness, then the easier band), so the first card
        equals `lemma_card`.

        Args:
            lemma_id: The lemma's deterministic id.
            gloss_language: Language of each card's gloss.
            translation_languages: Languages to fill the translations with.

        Returns:
            The cards (empty when the lemma is absent or has no sense).
        """
        rows = self._conn.execute(
            "SELECT s.lemma_id, s.concept_id, s.cefr_level, s.sense_frequency"
            " FROM senses s JOIN concepts c ON c.id = s.concept_id"
            " WHERE s.lemma_id = ?"
            " ORDER BY s.sense_frequency DESC NULLS LAST,"
            " c.commonness DESC NULLS LAST, s.cefr_level ASC NULLS LAST,"
            " s.concept_id",
            (lemma_id,),
        ).fetchall()
        return self._fill_cards(
            rows,
            gloss_language=gloss_language,
            translation_languages=translation_languages,
        )

    def _select_cards(
        self,
        where: str,
        params: tuple[object, ...],
        *,
        order: str,
        gloss_language: str,
        translation_languages: Sequence[str],
    ) -> list[LemmaCard]:
        """Run the card SELECT (``params`` ends with the limit) and fill each card."""
        sql = (
            "SELECT lemma_id, concept_id, cefr_level, sense_frequency"  # noqa: S608
            f" FROM lemma_drill d WHERE {where} ORDER BY {order} LIMIT ?"
        )
        rows = self._conn.execute(sql, params).fetchall()
        return self._fill_cards(
            rows,
            gloss_language=gloss_language,
            translation_languages=translation_languages,
        )

    def _fill_cards(
        self,
        rows: Sequence[sqlite3.Row],
        *,
        gloss_language: str,
        translation_languages: Sequence[str],
    ) -> list[LemmaCard]:
        """Build one card per ``(lemma_id, concept_id, cefr, frequency)`` row."""
        lemmas = self._lemmas_by_ids(sorted({r["lemma_id"] for r in rows}))
        concept_ids = sorted({r["concept_id"] for r in rows if r["concept_id"]})
        concepts = self._card_concepts(concept_ids)
        translations = self._card_translations(concept_ids, translation_languages)
        cards: list[LemmaCard] = []
        for row in rows:
            lemma = lemmas[row["lemma_id"]]
            cid = row["concept_id"]
            definitions, examples = concepts.get(cid, ({}, {}))
            cards.append(
                LemmaCard(
                    lemma=lemma,
                    concept_id=cid,
                    cefr_level=row["cefr_level"],
                    sense_frequency=row["sense_frequency"],
                    gloss=definitions.get(gloss_language),
                    translations={
                        language: [
                            text
                            for lid, text in translations.get((cid, language), [])
                            if lid != lemma.id
                        ]
                        for language in translation_languages
                    },
                    examples=list(examples.get(lemma.language, [])),
                ),
            )
        return cards

    def _lemmas_by_ids(self, lemma_ids: Sequence[str]) -> dict[str, Lemma]:
        """Return ``lemma_id -> Lemma`` for a page of cards."""
        if not lemma_ids:
            return {}
        marks = ", ".join("?" for _ in lemma_ids)
        lemmas: list[Lemma] = self._query(
            "lemmas",
            f"SELECT {_select_cols('lemmas')} FROM lemmas WHERE id IN ({marks})",  # noqa: S608
            tuple(lemma_ids),
        )
        return {lemma.id: lemma for lemma in lemmas}

    def _card_concepts(
        self,
        concept_ids: Sequence[str],
    ) -> dict[str, tuple[dict[str, str], dict[str, list[str]]]]:
        """Return ``concept_id -> (definitions, examples)`` for a page of cards."""
        if not concept_ids:
            return {}
        marks = ", ".join("?" for _ in concept_ids)
        rows = self._conn.execute(
            f"SELECT id, definitions, examples FROM concepts WHERE id IN ({marks})",  # noqa: S608
            tuple(concept_ids),
        ).fetchall()
        return {
            row["id"]: (
                json.loads(row["definitions"] or "{}"),
                json.loads(row["examples"] or "{}"),
            )
            for row in rows
        }

    def _card_translations(
        self,
        concept_ids: Sequence[str],
        languages: Sequence[str],
    ) -> dict[tuple[str, str], list[tuple[str, str]]]:
        """Return ``(concept_id, language) -> [(lemma_id, text)]``, by frequency."""
        if not concept_ids or not languages:
            return {}
        c_marks = ", ".join("?" for _ in concept_ids)
        l_marks = ", ".join("?" for _ in languages)
        rows = self._conn.execute(
            "SELECT s.concept_id, l.language, l.id, l.text FROM senses s"  # noqa: S608
            # CROSS JOIN pins the join order: drive from the concept index on
            # senses, not from the (far less selective) lemma language index.
            " CROSS JOIN lemmas l ON l.id = s.lemma_id"
            f" WHERE s.concept_id IN ({c_marks})"
            f" AND l.language IN ({l_marks})"
            " ORDER BY s.sense_frequency DESC NULLS LAST, l.text",
            (*concept_ids, *languages),
        ).fetchall()
        out: dict[tuple[str, str], list[tuple[str, str]]] = defaultdict(list)
        for row in rows:
            out[row["concept_id"], row["language"]].append((row["id"], row["text"]))
        return out

    # --- Concept reads ---------------------------------------------------

    def get_all_concepts(self) -> list[Concept]:
        """Return all concepts."""
        return self._query(
            "concepts",
            f"SELECT {_select_cols('concepts')} FROM concepts",  # noqa: S608
        )

    def get_concept_by_id(self, concept_id: str) -> Concept | None:
        """Look up a concept by its id (None when absent)."""
        rows = self._query(
            "concepts",
            f"SELECT {_select_cols('concepts')} FROM concepts WHERE id = ?",  # noqa: S608
            (concept_id,),
        )
        return rows[0] if rows else None

    # --- Adjacency reads -------------------------------------------------

    def senses_for_lemma(self, lemma_id: str) -> list[Sense]:
        """Return the sense edges of a lemma (empty when absent)."""
        return self._query(
            "senses",
            f"SELECT {_select_cols('senses')} FROM senses WHERE lemma_id = ?",  # noqa: S608
            (lemma_id,),
        )

    def senses_for_concept(self, concept_id: str) -> list[Sense]:
        """Return the sense edges into a concept (empty when absent)."""
        return self._query(
            "senses",
            f"SELECT {_select_cols('senses')} FROM senses WHERE concept_id = ?",  # noqa: S608
            (concept_id,),
        )

    def concepts_for_lemma(self, lemma_id: str) -> list[Concept]:
        """Return the concepts a lemma realises, de-duplicated (empty when absent)."""
        concepts = self._query(
            "concepts",
            f"SELECT {_select_cols('concepts', 'c')} FROM senses s "  # noqa: S608
            "JOIN concepts c ON c.id = s.concept_id WHERE s.lemma_id = ?",
            (lemma_id,),
        )
        return _dedupe_by_id(concepts)

    def lemmas_for_concept(
        self,
        concept_id: str,
        language: str | None = None,
    ) -> list[Lemma]:
        """Return the lemmas realising a concept, optionally filtered by language."""
        sql = (
            f"SELECT {_select_cols('lemmas', 'l')} FROM senses s "  # noqa: S608
            "JOIN lemmas l ON l.id = s.lemma_id WHERE s.concept_id = ?"
        )
        params: tuple[object, ...] = (concept_id,)
        if language is not None:
            sql += " AND l.language = ?"
            params = (concept_id, language)
        return self._query("lemmas", sql, params)

    def get_false_friends_for_lemma(
        self,
        lemma_id: str,
    ) -> list[tuple[Lemma, FalseFriendRelation]]:
        """Return each false friend of a lemma as ``(other_lemma, edge)``."""
        edges = self._query(
            "false_friends",
            f"SELECT {_select_cols('false_friends')} FROM false_friends "  # noqa: S608
            "WHERE lemma_id_a = ? OR lemma_id_b = ?",
            (lemma_id, lemma_id),
        )
        out: list[tuple[Lemma, FalseFriendRelation]] = []
        for edge in edges:
            other_id = (
                edge.lemma_id_b if edge.lemma_id_a == lemma_id else edge.lemma_id_a
            )
            other = self.get_lemma_by_id(other_id)
            if other is not None:
                out.append((other, edge))
        return out

    def concept_relations_for(
        self,
        concept_id: str,
        relation_type: str | None = None,
    ) -> list[ConceptRelation]:
        """Return the concept relations touching a concept.

        For directional types the edge is returned as stored (the concept may be
        the source or the target); for symmetric types the canonical ordering
        already made the pair unique. Optionally filter by `relation_type`.

        Args:
            concept_id: The concept whose relations to fetch.
            relation_type: Restrict to a single relation type when given.

        Returns:
            The matching relation edges (empty when absent).
        """
        sql = (
            f"SELECT {_select_cols('concept_relations')} FROM concept_relations "  # noqa: S608
            "WHERE (concept_id_a = ? OR concept_id_b = ?)"
        )
        params: tuple[object, ...] = (concept_id, concept_id)
        if relation_type is not None:
            sql += " AND relation_type = ?"
            params = (concept_id, concept_id, relation_type)
        return self._query("concept_relations", sql, params)

    def sense_relations_for(
        self,
        sense_id: str,
        relation_type: str | None = None,
    ) -> list[SenseRelation]:
        """Return the sense relations touching a sense (e.g. its antonyms).

        Symmetric edges are stored once in canonical order, so the sense may be
        either endpoint. Optionally filter by `relation_type`.

        Args:
            sense_id: The `Sense.id` whose relations to fetch.
            relation_type: Restrict to a single relation type when given.

        Returns:
            The matching relation edges (empty when absent).
        """
        sql = (
            f"SELECT {_select_cols('sense_relations')} FROM sense_relations "  # noqa: S608
            "WHERE (sense_id_a = ? OR sense_id_b = ?)"
        )
        params: tuple[object, ...] = (sense_id, sense_id)
        if relation_type is not None:
            sql += " AND relation_type = ?"
            params = (sense_id, sense_id, relation_type)
        return self._query("sense_relations", sql, params)

    # --- On-demand hydration (bounded, opt-in, fresh instances) ----------

    def hydrate_lemma(self, lemma: Lemma) -> Lemma:
        """Fill `lemma`'s back-references from SQLite (its senses and concepts).

        Bounded to 1-2 hops and built fresh on each call (no shared-instance
        identity). After this, `lemma.resolve_senses()` / `resolve_concepts()`
        return populated lists instead of raising.

        Args:
            lemma: The lemma to hydrate in place.

        Returns:
            The same `lemma`, with its back-references populated.
        """
        senses = self.senses_for_lemma(lemma.id)
        for sense in senses:
            sense.lemma = lemma
            sense.concept = self.get_concept_by_id(sense.concept_id)
        lemma.senses = senses
        lemma.concepts = _dedupe_by_id(
            [s.concept for s in senses if s.concept is not None],
        )
        return lemma

    def hydrate_concept(self, concept: Concept) -> Concept:
        """Fill `concept`'s back-references from SQLite (its senses and lemmas).

        Args:
            concept: The concept to hydrate in place.

        Returns:
            The same `concept`, with its back-references populated.
        """
        senses = self.senses_for_concept(concept.id)
        grouped: dict[str, list[Lemma]] = defaultdict(list)
        for sense in senses:
            sense.concept = concept
            sense.lemma = self.get_lemma_by_id(sense.lemma_id)
            if sense.lemma is not None:
                grouped[sense.lemma.language].append(sense.lemma)
        concept.senses = senses
        concept.lemmas = dict(grouped)
        return concept

    def hydrate_sense(self, sense: Sense) -> Sense:
        """Fill a sense's `lemma` / `concept` endpoints from SQLite.

        Args:
            sense: The sense edge to hydrate in place.

        Returns:
            The same `sense`, with both endpoints populated.
        """
        sense.lemma = self.get_lemma_by_id(sense.lemma_id)
        sense.concept = self.get_concept_by_id(sense.concept_id)
        return sense


def _corpus_present(data_fol: Path) -> bool:
    """Return True when a Parquet corpus exists under ``<data_fol>/lexicon/``."""
    lex = data_fol / LEXICON_SUBDIR
    return (lex / "concepts.parquet").exists() or (lex / "lemmas").is_dir()


def _load_corpus_models(data_fol: Path) -> dict[str, list]:
    """Load every table as models from the Parquet corpus.

    Args:
        data_fol: Project data folder; the corpus lives under
            ``<data_fol>/lexicon/``.

    Returns:
        The validated models per table.

    Raises:
        CorpusNotFoundError: When no Parquet corpus is present.
    """
    if not _corpus_present(data_fol):
        raise CorpusNotFoundError(data_fol / LEXICON_SUBDIR)
    return {name: _load_table(name, data_fol=data_fol) for name in TABLES}


#: Process-wide default store, built lazily on first `get_store()` call so that
#: importing this module never touches disk (a fresh checkout has no Parquet
#: until the parquetize notebook or the ingestion phase produces it).
_store: LexiconStore | None = None


def get_store() -> LexiconStore:
    """Return the process-wide default store, building it on first use.

    Raises:
        CorpusNotFoundError: When no Parquet corpus is present at the configured
            data folder.
    """
    global _store  # noqa: PLW0603 - module-level lazy singleton
    if _store is None:
        _store = LexiconStore.from_data_fol(get_lang_tools_params().paths.data_fol)
    return _store


def set_store(store: LexiconStore) -> None:
    """Override the process-wide default store (tests / fixtures)."""
    global _store  # noqa: PLW0603 - module-level lazy singleton
    _store = store


def reset_store() -> None:
    """Drop the cached default store so the next `get_store()` rebuilds it."""
    global _store  # noqa: PLW0603 - module-level lazy singleton
    _store = None


# --- Module-level delegating helpers (the stable read surface) -----------


def get_all_lemmas() -> list[Lemma]:
    """Return all lemmas."""
    return get_store().get_all_lemmas()


def get_lemma_by_id(lemma_id: str) -> Lemma | None:
    """Look up a lemma by its deterministic id."""
    return get_store().get_lemma_by_id(lemma_id)


def get_lemmas_by_language(language: str) -> list[Lemma]:
    """Filter lemmas by language code."""
    return get_store().get_lemmas_by_language(language)


def get_lemmas_by_topic(topic: str) -> list[Lemma]:
    """Filter lemmas containing a given topic tag."""
    return get_store().get_lemmas_by_topic(topic)


def get_lemmas_filtered(
    language: str | None = None,
    topic: str | None = None,
    *,
    query: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[Lemma]:
    """Filter lemmas by language, topic and/or search prefix, optionally paged."""
    return get_store().get_lemmas_filtered(
        language=language,
        topic=topic,
        query=query,
        limit=limit,
        offset=offset,
    )


def count_lemmas_filtered(
    language: str | None = None,
    topic: str | None = None,
    *,
    query: str | None = None,
) -> int:
    """Count the lemmas matching the filters."""
    return get_store().count_lemmas_filtered(
        language=language, topic=topic, query=query
    )


def lemma_cards(query: CardQuery) -> list[LemmaCard]:
    """Return the drill cards matching a `CardQuery`."""
    return get_store().lemma_cards(query)


def lemma_card(
    lemma_id: str,
    *,
    gloss_language: str = "en",
    translation_languages: Sequence[str] = ("en",),
) -> LemmaCard | None:
    """Return the drill card of one lemma (None when absent)."""
    return get_store().lemma_card(
        lemma_id,
        gloss_language=gloss_language,
        translation_languages=translation_languages,
    )


def lemma_sense_cards(
    lemma_id: str,
    *,
    gloss_language: str = "en",
    translation_languages: Sequence[str] = ("en",),
) -> list[LemmaCard]:
    """Return one card per sense of a lemma, best sense first."""
    return get_store().lemma_sense_cards(
        lemma_id,
        gloss_language=gloss_language,
        translation_languages=translation_languages,
    )


def get_all_concepts() -> list[Concept]:
    """Return all concepts."""
    return get_store().get_all_concepts()


def get_concept_by_id(concept_id: str) -> Concept | None:
    """Look up a concept by its id."""
    return get_store().get_concept_by_id(concept_id)


def senses_for_lemma(lemma_id: str) -> list[Sense]:
    """Return the sense edges of a lemma."""
    return get_store().senses_for_lemma(lemma_id)


def senses_for_concept(concept_id: str) -> list[Sense]:
    """Return the sense edges into a concept."""
    return get_store().senses_for_concept(concept_id)


def concepts_for_lemma(lemma_id: str) -> list[Concept]:
    """Return the concepts a lemma realises."""
    return get_store().concepts_for_lemma(lemma_id)


def lemmas_for_concept(concept_id: str, language: str | None = None) -> list[Lemma]:
    """Return the lemmas realising a concept, optionally filtered by language."""
    return get_store().lemmas_for_concept(concept_id, language=language)


def get_false_friends_for_lemma(
    lemma_id: str,
) -> list[tuple[Lemma, FalseFriendRelation]]:
    """Return each false friend of a lemma as ``(other_lemma, edge)``."""
    return get_store().get_false_friends_for_lemma(lemma_id)


def concept_relations_for(
    concept_id: str,
    relation_type: str | None = None,
) -> list[ConceptRelation]:
    """Return the concept relations touching a concept."""
    return get_store().concept_relations_for(concept_id, relation_type=relation_type)


def sense_relations_for(
    sense_id: str,
    relation_type: str | None = None,
) -> list[SenseRelation]:
    """Return the sense relations touching a sense (e.g. its antonyms)."""
    return get_store().sense_relations_for(sense_id, relation_type=relation_type)
