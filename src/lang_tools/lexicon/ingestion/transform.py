"""Transform stage: OMW backbone -> source-tagged tables.

This is the pure, deterministic core of the initial build. It takes the OMW
synset entries (the concept backbone) and produces the five lexical tables, each
row carrying a single lightweight provenance tag so a future re-ingestion merge
can refresh machine rows while leaving hand-curated (`manual`) rows alone.

Provenance policy (one tag per row, the seam the deferred merge needs):

- Every lemma/sense **originates** from OMW, so its tag is ``omw``. A concept is
  ``omw`` too, unless its English gloss came from the CILI/ILI fallback (phase
  5.5 Step 2), in which case it is ``cili`` - both permissive. The per-concept
  tags are decided in `group_to_records` (which owns the fallback) and threaded
  through here.
- ``SOURCE_KAIKKI`` remains defined as a **legacy** provenance value: the kaikki
  enrichment leg was removed in phase 5.5 (the sense-blind join produced the
  `house` defect and was the only CC-BY-SA source), so no row this stage writes
  is ever tagged ``kaikki``. The value is kept only so old Parquet that still
  carries it round-trips through the codec.

The optional LLM granularity-collapse pass is a deferred seam, not wired here:
the deterministic OMW-as-is output is the default and the only thing this stage
produces.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING

from lang_tools.lexicon.ingestion.sources.omw import SOURCE_OMW
from lang_tools.lexicon.ingestion.sources.omw import group_to_records

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping

    from lang_tools.lexicon.concept import Concept
    from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
    from lang_tools.lexicon.lemma import Lemma
    from lang_tools.lexicon.relations import ConceptRelation
    from lang_tools.lexicon.relations import FalseFriendRelation
    from lang_tools.lexicon.sense import Sense

#: Provenance tag values (the on-disk `codec.PROVENANCE_COL` column). ``SOURCE_OMW``
#: and ``SOURCE_CILI`` are owned by the OMW adapter (it emits those rows);
#: ``SOURCE_OMW`` is re-exported here so callers have one provenance vocabulary.
#: Legacy ``SOURCE_KAIKKI``: the kaikki enrichment leg was dropped in phase 5.5;
#: no row written today carries it, but old Parquet may still reference it.
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


def transform(
    omw_entries: Iterable[SynsetEntry],
    cili_glosses: Mapping[str, str] | None = None,
) -> TaggedTables:
    """Build the source-tagged lexical tables from the OMW backbone.

    Args:
        omw_entries: Flattened OMW synset entries (the concept backbone). OMW is
            the sole source of rows: definitions come from OMW glosses only,
            never from kaikki.
        cili_glosses: Optional ``{ili_id: english_gloss}`` map from the `cili`
            loader, used only to fill a concept's missing English gloss (tagged
            ``cili``); ``None`` disables the fallback.

    Returns:
        The populated `TaggedTables`. Lemmas/senses are tagged ``omw``; concepts
        are ``omw`` or ``cili`` per `group_to_records` (false-friend /
        concept-relation tables stay empty - those arrive in phase 7).
    """
    concepts, lemmas, senses, concept_sources = group_to_records(
        omw_entries,
        cili_glosses,
    )

    return TaggedTables(
        lemmas=lemmas,
        lemma_sources=[SOURCE_OMW] * len(lemmas),
        concepts=concepts,
        concept_sources=concept_sources,
        senses=senses,
        sense_sources=[SOURCE_OMW] * len(senses),
    )
