"""Transform stage: OMW backbone + kaikki enrichment -> source-tagged tables.

This is the pure, deterministic core of the initial build. It takes the OMW
synset entries (the concept backbone) and the kaikki enrichment entries and
produces the five lexical tables, each row carrying a single lightweight
provenance tag so a future re-ingestion merge can refresh machine rows while
leaving hand-curated (`manual`) rows alone.

Provenance policy (one tag per row, the seam the deferred merge needs):

- Every concept/lemma/sense **originates** from OMW, so its default tag is
  ``omw``.
- kaikki is enrichment only: it never adds rows, it fills sparse
  `Concept.definitions` and attaches `Lemma.examples`. Because kaikki text is
  CC-BY-SA, any row that ends up carrying kaikki content is re-tagged ``kaikki``
  (the conservative, license-isolating choice - it flags exactly the rows the
  share-alike obligation can touch). Senses carry no text, so they stay ``omw``.

The optional LLM granularity-collapse pass is a deferred seam, not wired here:
the deterministic OMW-as-is output is the default and the only thing this stage
produces.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from lang_tools.lexicon.ingestion.sources.omw import group_to_records

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from lang_tools.lexicon.concept import Concept
    from lang_tools.lexicon.ingestion.sources.kaikki import KaikkiEntry
    from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
    from lang_tools.lexicon.lemma import Lemma
    from lang_tools.lexicon.relations import ConceptRelation
    from lang_tools.lexicon.relations import FalseFriendRelation
    from lang_tools.lexicon.sense import Sense

#: Provenance tag values (the on-disk `codec.PROVENANCE_COL` column).
SOURCE_OMW = "omw"
SOURCE_KAIKKI = "kaikki"
SOURCE_LLM = "llm"
SOURCE_MANUAL = "manual"


@dataclass
class TaggedTables:
    """The five lexical tables, each as parallel ``(models, source-tags)`` lists.

    Keeping the tags parallel to the models (rather than on the models) mirrors
    the codec: provenance is an on-disk-only column the thin models never carry.

    Attributes:
        lemmas: Thin lexical tokens and their per-row provenance tags.
        concepts: Synsets and their tags.
        senses: Lemma <-> concept edges and their tags (always ``omw`` here).
        false_friends: False-friend edges; empty in the initial build (phase 7).
        concept_relations: Concept edges; empty in the initial build (phase 7).
    """

    lemmas: list[Lemma] = field(default_factory=list)
    lemma_sources: list[str] = field(default_factory=list)
    concepts: list[Concept] = field(default_factory=list)
    concept_sources: list[str] = field(default_factory=list)
    senses: list[Sense] = field(default_factory=list)
    sense_sources: list[str] = field(default_factory=list)
    false_friends: list[FalseFriendRelation] = field(default_factory=list)
    false_friend_sources: list[str] = field(default_factory=list)
    concept_relations: list[ConceptRelation] = field(default_factory=list)
    concept_relation_sources: list[str] = field(default_factory=list)


def _enrich_concepts(
    concepts: list[Concept],
    senses: list[Sense],
    lemmas: list[Lemma],
    enrichment: Mapping[tuple[str, str], KaikkiEntry],
) -> list[str]:
    """Fill sparse `Concept.definitions` from kaikki; return per-concept tags.

    A concept's missing per-language gloss is filled from the kaikki entry of any
    of that concept's lemmas in that language. A concept that gains any kaikki
    gloss is tagged `SOURCE_KAIKKI`, else `SOURCE_OMW`.
    """
    lemma_by_id = {lemma.id: lemma for lemma in lemmas}
    lemmas_by_concept: dict[str, list[Lemma]] = {}
    for sense in senses:
        lemma = lemma_by_id.get(sense.lemma_id)
        if lemma is not None:
            lemmas_by_concept.setdefault(sense.concept_id, []).append(lemma)

    tags: list[str] = []
    for concept in concepts:
        touched = False
        for lemma in lemmas_by_concept.get(concept.id, []):
            if lemma.language in concept.definitions:
                continue
            entry = enrichment.get((lemma.normalized, lemma.language))
            if entry is not None and entry.definitions:
                concept.definitions[lemma.language] = entry.definitions[0]
                touched = True
        tags.append(SOURCE_KAIKKI if touched else SOURCE_OMW)
    return tags


def _enrich_lemmas(
    lemmas: list[Lemma],
    enrichment: Mapping[tuple[str, str], KaikkiEntry],
) -> list[str]:
    """Attach kaikki example sentences to lemmas; return per-lemma tags."""
    tags: list[str] = []
    for lemma in lemmas:
        entry = enrichment.get((lemma.normalized, lemma.language))
        if entry is not None and entry.examples:
            lemma.examples = [*lemma.examples, *entry.examples]
            if SOURCE_KAIKKI not in lemma.sources:
                lemma.sources = [*lemma.sources, SOURCE_KAIKKI]
            tags.append(SOURCE_KAIKKI)
        else:
            tags.append(SOURCE_OMW)
    return tags


def transform(
    omw_entries: Iterable[SynsetEntry],
    kaikki_entries: Iterable[KaikkiEntry] = (),
) -> TaggedTables:
    """Build the source-tagged lexical tables from OMW + kaikki inputs.

    Args:
        omw_entries: Flattened OMW synset entries (the concept backbone).
        kaikki_entries: Optional enrichment entries; when empty the output is
            pure deterministic OMW-as-is.

    Returns:
        The populated `TaggedTables` (false-friend / concept-relation tables stay
        empty - those arrive in phase 7).
    """
    concepts, lemmas, senses = group_to_records(omw_entries)

    # kaikki only ever joins onto an OMW lemma, so the usable key set is exactly
    # the OMW lemma keys - bounded by the backbone, independent of dump size.
    # Stream the entries and keep only matching ones, so peak memory is |needed|
    # rather than the (multi-hundred-MB) kaikki dumps. `kaikki_entries` must reach
    # here as a lazy iterator (see `pipeline.load_sources`); never list() it.
    needed = {(lem.normalized, lem.language) for lem in lemmas}
    enrichment: dict[tuple[str, str], KaikkiEntry] = {}
    for entry in kaikki_entries:
        key = entry.key
        # First entry per key wins (kaikki dumps can repeat a headword).
        if key in needed and key not in enrichment:
            enrichment[key] = entry

    concept_tags = _enrich_concepts(concepts, senses, lemmas, enrichment)
    lemma_tags = _enrich_lemmas(lemmas, enrichment)

    return TaggedTables(
        lemmas=lemmas,
        lemma_sources=lemma_tags,
        concepts=concepts,
        concept_sources=concept_tags,
        senses=senses,
        sense_sources=[SOURCE_OMW] * len(senses),
    )
