"""In-memory read/query store for the whole lexical graph.

The store is the read layer over lemmas, concepts, senses, and the decoupled
relation edges. It loads each table through the Parquet codec seam
(`lang_tools.lexicon.codec`), builds the look-aside indexes the app needs, and
hydrates the representation-layer back-references (`sense.lemma`, `lemma.senses`,
`concept.lemmas`, ...) that the persisted models leave empty.

Runtime modes (from the phase-3 memory cliff):
    The full corpus as in-memory pydantic dicts is ~1.9 GB resident, infeasible
    on a small dyno, so the store exposes **one query surface** over two
    interchangeable engines. **Resident mode** (the default, used for the small
    bootstrap/sample data) loads every table into dicts and hydrates the whole
    graph eagerly. **SQLite mode** (for the full corpus) serves the same surface
    from indexed ``SELECT``s at ~0 resident; its indexed implementation lands
    with phase-5 data, so this phase ships the seam (the `LexiconStoreMode`
    switch) with resident mode implemented and SQLite mode raising a clear,
    not-yet-implemented error.

Sample-data note:
    Until phase 9 regenerates the sample corpus as Parquet, the default store
    keeps sourcing its **lemmas** from the existing bootstrap CSVs (the resident
    sample data); the concept/sense/edge tables load from Parquet under
    ``data/lexicon/`` and are empty until the ingestion phase produces them.
"""

from __future__ import annotations

from collections import defaultdict
from enum import StrEnum
from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.lexicon.codec import StoreDependencyMissingError
from lang_tools.lexicon.codec import _load_table
from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.ingestion.csv_loader import load_csv
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.sense import Sense
from lang_tools.params.lang_tools_params import get_lang_tools_params

if TYPE_CHECKING:
    from pathlib import Path

    from lang_tools.lexicon.relations import ConceptRelation
    from lang_tools.lexicon.relations import FalseFriendRelation

# Resolve the circular back-reference annotations (Lemma <-> Sense <-> Concept)
# now that all three classes are importable in this namespace. model_rebuild
# picks the classes up from this module's globals; a TYPE_CHECKING-only import in
# the model modules is not enough for the runtime rebuild.
Sense.model_rebuild()
Concept.model_rebuild()
Lemma.model_rebuild()


class LexiconStoreMode(StrEnum):
    """Access engine behind the store's single query surface."""

    RESIDENT = "resident"
    SQLITE = "sqlite"


class SqliteModeNotImplementedError(NotImplementedError):
    """Raised when SQLite mode is requested before its phase-5 implementation."""

    def __init__(self) -> None:
        """Initialize with a fixed, descriptive message."""
        super().__init__(
            "SQLite store mode is specified but not implemented yet; it lands "
            "with the full-corpus data in phase 5. Use resident mode for now.",
        )


def _dedupe_by_id(items: list[Concept]) -> list[Concept]:
    """Return concepts unique by id, preserving first-seen order."""
    seen: set[str] = set()
    out: list[Concept] = []
    for item in items:
        if item.id not in seen:
            seen.add(item.id)
            out.append(item)
    return out


class LexiconStore:
    """Read/query store over the whole lexical graph (resident mode).

    Attributes:
        mode: The access engine in use (`LexiconStoreMode`).
    """

    def __init__(
        self,
        *,
        lemmas: list[Lemma],
        concepts: list[Concept],
        senses: list[Sense],
        false_friends: list[FalseFriendRelation],
        concept_relations: list[ConceptRelation],
        mode: LexiconStoreMode = LexiconStoreMode.RESIDENT,
        hydrate: bool = True,
    ) -> None:
        """Build the registries, indexes, and (optionally) hydrate the graph.

        Args:
            lemmas: All lemmas.
            concepts: All concepts.
            senses: All sense edges.
            false_friends: All false-friend edges.
            concept_relations: All concept-relation edges.
            mode: Access engine; only `LexiconStoreMode.RESIDENT` is implemented.
            hydrate: Populate the back-reference fields after indexing.

        Raises:
            SqliteModeNotImplementedError: If `mode` is SQLite.
        """
        if mode is LexiconStoreMode.SQLITE:
            raise SqliteModeNotImplementedError
        self.mode = mode

        self._all_lemmas = lemmas
        self._all_concepts = concepts
        self._all_senses = senses
        self._all_false_friends = false_friends
        self._all_concept_relations = concept_relations

        # Primary-key indexes (the hot point lookups).
        self._lemmas_by_id: dict[str, Lemma] = {lem.id: lem for lem in lemmas}
        self._concepts_by_id: dict[str, Concept] = {c.id: c for c in concepts}

        # Look-aside adjacency indexes.
        self._senses_by_lemma_id: dict[str, list[Sense]] = defaultdict(list)
        self._senses_by_concept_id: dict[str, list[Sense]] = defaultdict(list)
        for sense in senses:
            self._senses_by_lemma_id[sense.lemma_id].append(sense)
            self._senses_by_concept_id[sense.concept_id].append(sense)

        # A false-friend edge is stored once (canonical a < b); index it under
        # both endpoints so a lookup by either lemma finds it.
        self._false_friends_by_lemma_id: dict[str, list[FalseFriendRelation]] = (
            defaultdict(list)
        )
        for edge in false_friends:
            self._false_friends_by_lemma_id[edge.lemma_id_a].append(edge)
            self._false_friends_by_lemma_id[edge.lemma_id_b].append(edge)

        # Concept relations: index under both endpoints for traversal; the typed
        # query method below respects directional vs symmetric semantics.
        self._concept_relations_by_id: dict[str, list[ConceptRelation]] = defaultdict(
            list,
        )
        for rel in concept_relations:
            self._concept_relations_by_id[rel.concept_id_a].append(rel)
            self._concept_relations_by_id[rel.concept_id_b].append(rel)

        self._warn_on_slug_collisions()
        if hydrate:
            self._hydrate()

    @classmethod
    def from_data_fol(
        cls,
        data_fol: Path,
        *,
        lemmas: list[Lemma] | None = None,
        mode: LexiconStoreMode = LexiconStoreMode.RESIDENT,
        hydrate: bool = True,
    ) -> LexiconStore:
        """Load every table from the Parquet corpus and build the store.

        Args:
            data_fol: Project data folder; the corpus lives under
                ``<data_fol>/lexicon/``.
            lemmas: Override the lemma table (used by the default store to keep
                serving the bootstrap-CSV sample until phase 9). When None,
                lemmas load from Parquet like the other tables.
            mode: Access engine.
            hydrate: Populate back-references after indexing.

        Returns:
            The assembled store. Tables with no Parquet files load empty; if the
            optional ``store`` extra (pyarrow) is missing, the Parquet-backed
            tables load empty and a warning is logged.
        """
        try:
            loaded_lemmas = lemmas if lemmas is not None else _load_table(
                "lemmas",
                data_fol=data_fol,
            )
            concepts = _load_table("concepts", data_fol=data_fol)
            senses = _load_table("senses", data_fol=data_fol)
            false_friends = _load_table("false_friends", data_fol=data_fol)
            concept_relations = _load_table("concept_relations", data_fol=data_fol)
        except StoreDependencyMissingError:
            lg.warning(
                "Parquet codec unavailable (install the 'store' extra); "
                "concept/sense/edge tables load empty.",
            )
            loaded_lemmas = lemmas or []
            concepts, senses = [], []
            false_friends, concept_relations = [], []
        return cls(
            lemmas=loaded_lemmas,
            concepts=concepts,
            senses=senses,
            false_friends=false_friends,
            concept_relations=concept_relations,
            mode=mode,
            hydrate=hydrate,
        )

    def _warn_on_slug_collisions(self) -> None:
        """Warn when two concepts share a readable slug (ids stay unique via hash)."""
        ids_by_slug: dict[str, set[str]] = defaultdict(set)
        for concept in self._all_concepts:
            # id shape: c__{slug}__{hash[:12]}; the slug is everything between.
            slug = concept.id[len("c__") : concept.id.rfind("__")]
            ids_by_slug[slug].add(concept.id)
        for slug, ids in ids_by_slug.items():
            if len(ids) > 1:
                lg.warning("Concept slug collision: {!r} used by {}", slug, sorted(ids))

    def _hydrate(self) -> None:
        """Populate the serialization-excluded back-references across the graph."""
        for sense in self._all_senses:
            sense.lemma = self._lemmas_by_id.get(sense.lemma_id)
            sense.concept = self._concepts_by_id.get(sense.concept_id)

        for lemma in self._all_lemmas:
            lemma_senses = self._senses_by_lemma_id.get(lemma.id, [])
            lemma.senses = lemma_senses
            lemma.concepts = _dedupe_by_id(
                [s.concept for s in lemma_senses if s.concept is not None],
            )

        for concept in self._all_concepts:
            concept_senses = self._senses_by_concept_id.get(concept.id, [])
            concept.senses = concept_senses
            grouped: dict[str, list[Lemma]] = defaultdict(list)
            for sense in concept_senses:
                if sense.lemma is not None:
                    grouped[sense.lemma.language].append(sense.lemma)
            concept.lemmas = dict(grouped)

    # --- Lemma reads -----------------------------------------------------

    def get_all_lemmas(self) -> list[Lemma]:
        """Return all lemmas."""
        return self._all_lemmas

    def get_lemma_by_id(self, lemma_id: str) -> Lemma | None:
        """Look up a lemma by its deterministic id (None when absent)."""
        return self._lemmas_by_id.get(lemma_id)

    def get_lemmas_by_language(self, language: str) -> list[Lemma]:
        """Filter lemmas by language code."""
        return [lem for lem in self._all_lemmas if lem.language == language]

    def get_lemmas_by_topic(self, topic: str) -> list[Lemma]:
        """Filter lemmas carrying a given topic tag."""
        return [lem for lem in self._all_lemmas if topic in lem.topics]

    def get_lemmas_filtered(
        self,
        language: str | None = None,
        topic: str | None = None,
    ) -> list[Lemma]:
        """Filter lemmas by language and/or topic."""
        results = self._all_lemmas
        if language:
            results = [lem for lem in results if lem.language == language]
        if topic:
            results = [lem for lem in results if topic in lem.topics]
        return results

    # --- Concept reads ---------------------------------------------------

    def get_all_concepts(self) -> list[Concept]:
        """Return all concepts."""
        return self._all_concepts

    def get_concept_by_id(self, concept_id: str) -> Concept | None:
        """Look up a concept by its id (None when absent)."""
        return self._concepts_by_id.get(concept_id)

    # --- Adjacency reads -------------------------------------------------

    def senses_for_lemma(self, lemma_id: str) -> list[Sense]:
        """Return the sense edges of a lemma (empty when absent)."""
        return self._senses_by_lemma_id.get(lemma_id, [])

    def senses_for_concept(self, concept_id: str) -> list[Sense]:
        """Return the sense edges into a concept (empty when absent)."""
        return self._senses_by_concept_id.get(concept_id, [])

    def concepts_for_lemma(self, lemma_id: str) -> list[Concept]:
        """Return the concepts a lemma realises, de-duplicated (empty when absent)."""
        concepts = [
            self._concepts_by_id[s.concept_id]
            for s in self._senses_by_lemma_id.get(lemma_id, [])
            if s.concept_id in self._concepts_by_id
        ]
        return _dedupe_by_id(concepts)

    def lemmas_for_concept(
        self,
        concept_id: str,
        language: str | None = None,
    ) -> list[Lemma]:
        """Return the lemmas realising a concept, optionally filtered by language."""
        lemmas = [
            self._lemmas_by_id[s.lemma_id]
            for s in self._senses_by_concept_id.get(concept_id, [])
            if s.lemma_id in self._lemmas_by_id
        ]
        if language is not None:
            lemmas = [lem for lem in lemmas if lem.language == language]
        return lemmas

    def get_false_friends_for_lemma(
        self,
        lemma_id: str,
    ) -> list[tuple[Lemma, FalseFriendRelation]]:
        """Return each false friend of a lemma as ``(other_lemma, edge)``."""
        out: list[tuple[Lemma, FalseFriendRelation]] = []
        for edge in self._false_friends_by_lemma_id.get(lemma_id, []):
            other_id = (
                edge.lemma_id_b if edge.lemma_id_a == lemma_id else edge.lemma_id_a
            )
            other = self._lemmas_by_id.get(other_id)
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
        edges = self._concept_relations_by_id.get(concept_id, [])
        if relation_type is not None:
            edges = [e for e in edges if e.relation_type == relation_type]
        return edges


def _load_bootstrap_lemmas() -> list[Lemma]:
    """Load the bootstrap-CSV sample lemmas (the resident sample data)."""
    bootstrap_dir = get_lang_tools_params().paths.data_fol / "bootstrap"
    lemmas: list[Lemma] = []
    if not bootstrap_dir.exists():
        lg.warning("Bootstrap dir not found: {}", bootstrap_dir)
        return lemmas
    for csv_path in sorted(bootstrap_dir.glob("*.csv")):
        batch = list(load_csv(csv_path))
        lg.info("Loaded {} lemmas from {}", len(batch), csv_path.name)
        lemmas.extend(batch)
    lg.info("Lemma store initialized: {} total lemmas", len(lemmas))
    return lemmas


_STORE = LexiconStore.from_data_fol(
    get_lang_tools_params().paths.data_fol,
    lemmas=_load_bootstrap_lemmas(),
)


def get_store() -> LexiconStore:
    """Return the process-wide default store."""
    return _STORE


# --- Module-level delegating helpers (the stable read surface) -----------


def get_all_lemmas() -> list[Lemma]:
    """Return all bootstrap lemmas."""
    return _STORE.get_all_lemmas()


def get_lemma_by_id(lemma_id: str) -> Lemma | None:
    """Look up a lemma by its deterministic id."""
    return _STORE.get_lemma_by_id(lemma_id)


def get_lemmas_by_language(language: str) -> list[Lemma]:
    """Filter lemmas by language code."""
    return _STORE.get_lemmas_by_language(language)


def get_lemmas_by_topic(topic: str) -> list[Lemma]:
    """Filter lemmas containing a given topic tag."""
    return _STORE.get_lemmas_by_topic(topic)


def get_lemmas_filtered(
    language: str | None = None,
    topic: str | None = None,
) -> list[Lemma]:
    """Filter lemmas by language and/or topic."""
    return _STORE.get_lemmas_filtered(language=language, topic=topic)


def get_all_concepts() -> list[Concept]:
    """Return all concepts."""
    return _STORE.get_all_concepts()


def get_concept_by_id(concept_id: str) -> Concept | None:
    """Look up a concept by its id."""
    return _STORE.get_concept_by_id(concept_id)


def senses_for_lemma(lemma_id: str) -> list[Sense]:
    """Return the sense edges of a lemma."""
    return _STORE.senses_for_lemma(lemma_id)


def senses_for_concept(concept_id: str) -> list[Sense]:
    """Return the sense edges into a concept."""
    return _STORE.senses_for_concept(concept_id)


def concepts_for_lemma(lemma_id: str) -> list[Concept]:
    """Return the concepts a lemma realises."""
    return _STORE.concepts_for_lemma(lemma_id)


def lemmas_for_concept(concept_id: str, language: str | None = None) -> list[Lemma]:
    """Return the lemmas realising a concept, optionally filtered by language."""
    return _STORE.lemmas_for_concept(concept_id, language=language)


def get_false_friends_for_lemma(
    lemma_id: str,
) -> list[tuple[Lemma, FalseFriendRelation]]:
    """Return each false friend of a lemma as ``(other_lemma, edge)``."""
    return _STORE.get_false_friends_for_lemma(lemma_id)


def concept_relations_for(
    concept_id: str,
    relation_type: str | None = None,
) -> list[ConceptRelation]:
    """Return the concept relations touching a concept."""
    return _STORE.concept_relations_for(concept_id, relation_type=relation_type)
