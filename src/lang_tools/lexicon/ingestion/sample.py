"""Carve a small, committed sample slice out of the full lexical tables.

The full corpus is large and gitignored; `lang-tutor` and the test suite want a
tiny, deterministic slice they can load green. `carve_sample` keeps N concepts
together with the lemmas and senses connected to them, and drops any edge whose
endpoints fall outside the slice. Provenance tags travel with each kept row.

Which N (phase 05.59):
    Ranked, not the first N by id. Sorting by id alone is stable but arbitrary -
    it produced a seed of "15 May Organization", "1530s", "1750s", useless to the
    consumers the slice exists for. Concepts are ranked by how much a consumer can
    do with them: the most languages first, then having an example sentence, then
    id. The id tiebreak keeps the slice deterministic and stable across rebuilds,
    and the ranking degrades gracefully - a build where nothing is rich falls back
    to id order on its own, with no special case.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from lang_tools.lexicon.ingestion.transform import TaggedTables

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Sequence

#: Default number of concepts to keep in the committed sample slice.
DEFAULT_SAMPLE_CONCEPTS = 50


def _languages_per_concept(tables: TaggedTables) -> dict[str, set[str]]:
    """Map each concept id to the languages its members are written in."""
    lemma_language = {lemma.id: lemma.language for lemma in tables.lemmas}
    per_concept: dict[str, set[str]] = {}
    for sense in tables.senses:
        language = lemma_language.get(sense.lemma_id)
        if language is not None:
            per_concept.setdefault(sense.concept_id, set()).add(language)
    return per_concept

def _edges_within(
    edges: Sequence[Any],
    sources: Sequence[str],
    kept: set[str],
    endpoints: Callable[[Any], tuple[str, str]],
) -> tuple[list[Any], list[str]]:
    """Keep the edges (and their parallel tags) whose two endpoints are in `kept`."""
    out: list[Any] = []
    tags: list[str] = []
    for edge, tag in zip(edges, sources, strict=True):
        a, b = endpoints(edge)
        if a in kept and b in kept:
            out.append(edge)
            tags.append(tag)
    return out, tags


def carve_sample(
    tables: TaggedTables,
    *,
    max_concepts: int = DEFAULT_SAMPLE_CONCEPTS,
) -> TaggedTables:
    """Return a self-consistent slice of `tables` with at most `max_concepts`.

    The slice is closed under the kept concepts: a sense survives only if both
    its concept and its lemma survive, a lemma survives only if at least one of
    its senses does, and an edge (false-friend / concept-relation /
    sense-relation) survives only if both endpoints do. This keeps the slice
    loadable without dangling ids.

    Concepts are ranked before the cap (see the module docstring): most languages
    first, then having an example, then id ascending.

    Args:
        tables: The full source-tagged tables.
        max_concepts: How many concepts to keep, best-ranked first.

    Returns:
        A new `TaggedTables` holding only the slice; the input is not mutated.
    """
    languages = _languages_per_concept(tables)
    order = sorted(
        range(len(tables.concepts)),
        key=lambda i: (
            -len(languages.get(tables.concepts[i].id, ())),
            not tables.concepts[i].examples,
            tables.concepts[i].id,
        ),
    )
    keep_idx = order[:max_concepts]
    kept_concepts = [tables.concepts[i] for i in keep_idx]
    kept_concept_tags = [tables.concept_sources[i] for i in keep_idx]
    kept_concept_ids = {c.id for c in kept_concepts}

    senses: list = []
    sense_tags: list[str] = []
    used_lemma_ids: set[str] = set()
    for sense, tag in zip(tables.senses, tables.sense_sources, strict=True):
        if sense.concept_id in kept_concept_ids:
            senses.append(sense)
            sense_tags.append(tag)
            used_lemma_ids.add(sense.lemma_id)
    kept_sense_ids = {sense.id for sense in senses}

    lemmas: list = []
    lemma_tags: list[str] = []
    for lemma, tag in zip(tables.lemmas, tables.lemma_sources, strict=True):
        if lemma.id in used_lemma_ids:
            lemmas.append(lemma)
            lemma_tags.append(tag)

    ff, ff_tags = _edges_within(
        tables.false_friends,
        tables.false_friend_sources,
        used_lemma_ids,
        lambda edge: (edge.lemma_id_a, edge.lemma_id_b),
    )
    rels, rel_tags = _edges_within(
        tables.concept_relations,
        tables.concept_relation_sources,
        kept_concept_ids,
        lambda edge: (edge.concept_id_a, edge.concept_id_b),
    )
    sense_rels, sense_rel_tags = _edges_within(
        tables.sense_relations,
        tables.sense_relation_sources,
        kept_sense_ids,
        lambda edge: (edge.sense_id_a, edge.sense_id_b),
    )

    return TaggedTables(
        lemmas=lemmas,
        lemma_sources=lemma_tags,
        concepts=kept_concepts,
        concept_sources=kept_concept_tags,
        senses=senses,
        sense_sources=sense_tags,
        false_friends=ff,
        false_friend_sources=ff_tags,
        concept_relations=rels,
        concept_relation_sources=rel_tags,
        sense_relations=sense_rels,
        sense_relation_sources=sense_rel_tags,
    )
