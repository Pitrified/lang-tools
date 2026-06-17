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

#: Bump to invalidate every persisted SQLite cache after a schema/codec change.
CACHE_VERSION = 1

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
)

#: Columns stored as JSON text in SQLite (the list / dict model fields). Every
#: other column binds to a native SQLite value.
_JSON_COLUMNS: dict[str, frozenset[str]] = {
    "lemmas": frozenset({"topics", "examples", "sources"}),
    "concepts": frozenset({"definitions"}),
    "senses": frozenset(),
    "false_friends": frozenset({"explanation_notes"}),
    "concept_relations": frozenset(),
}

#: Secondary indexes per table (beyond the implicit primary key on ``id``).
_INDEXES: dict[str, tuple[str, ...]] = {
    "lemmas": ("language",),
    "concepts": (),
    "senses": ("lemma_id", "concept_id"),
    "false_friends": ("lemma_id_a", "lemma_id_b"),
    "concept_relations": ("concept_id_a", "concept_id_b"),
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


def _new_conn(target: str) -> sqlite3.Connection:
    """Open a SQLite connection with the row factory the store relies on."""
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row
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
        db_path: Path | None = None,
    ) -> LexiconStore:
        """Build a store by loading model lists into a fresh SQLite database.

        Args:
            lemmas: All lemmas.
            concepts: All concepts.
            senses: All sense edges.
            false_friends: All false-friend edges.
            concept_relations: All concept-relation edges.
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
            },
        )
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
        """Filter lemmas carrying a given topic tag."""
        return [lem for lem in self.get_all_lemmas() if topic in lem.topics]

    def get_lemmas_filtered(
        self,
        language: str | None = None,
        topic: str | None = None,
    ) -> list[Lemma]:
        """Filter lemmas by language and/or topic."""
        results = (
            self.get_lemmas_by_language(language)
            if language
            else self.get_all_lemmas()
        )
        if topic:
            results = [lem for lem in results if topic in lem.topics]
        return results

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
) -> list[Lemma]:
    """Filter lemmas by language and/or topic."""
    return get_store().get_lemmas_filtered(language=language, topic=topic)


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
