"""Tests for the transform stage (`ingestion.transform`)."""

from lang_tools.lexicon.ingestion.sources.omw import SOURCE_CILI
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.transform import SOURCE_KAIKKI
from lang_tools.lexicon.ingestion.transform import SOURCE_OMW
from lang_tools.lexicon.ingestion.transform import transform


def _omw() -> list[SynsetEntry]:
    return [
        SynsetEntry("en", "en-1", "i1", "a building for living", ("house",), "n"),
        # pt synset shares the ILI but has no gloss; without kaikki it stays empty.
        SynsetEntry("pt", "pt-1", "i1", None, ("casa",), "n"),
    ]


def test_omw_tags_everything_omw() -> None:
    tables = transform(_omw())
    assert set(tables.concept_sources) == {SOURCE_OMW}
    assert set(tables.lemma_sources) == {SOURCE_OMW}
    assert set(tables.sense_sources) == {SOURCE_OMW}
    # The pt gloss stays empty: OMW left it blank and there is no enrichment.
    assert tables.concepts[0].definitions == {"en": "a building for living"}


def test_no_row_is_tagged_kaikki() -> None:
    # The kaikki enrichment leg was removed in phase 5.5: nothing the build writes
    # may carry the (legacy) kaikki provenance tag. This is the standing guard.
    tables = transform(_omw())
    all_tags = (
        tables.lemma_sources
        + tables.concept_sources
        + tables.sense_sources
        + tables.false_friend_sources
        + tables.concept_relation_sources
    )
    assert SOURCE_KAIKKI not in all_tags


def test_cili_fallback_tags_concept_cili() -> None:
    # An ILI-backed concept with no English OMW gloss gets its English gloss from
    # the CILI fallback, and that concept row is tagged cili; lemmas/senses stay
    # omw (CILI only touches the concept gloss).
    entries = [
        SynsetEntry(
            "pt", "pt-1", "i9", "uma moradia", ("casa",), "n",
            ili_definition="a building for living",
        ),
    ]
    tables = transform(entries)
    assert tables.concepts[0].definitions["en"] == "a building for living"
    assert tables.concept_sources == [SOURCE_CILI]
    assert set(tables.lemma_sources) == {SOURCE_OMW}
    assert SOURCE_KAIKKI not in tables.concept_sources


def test_relation_tables_stay_empty() -> None:
    tables = transform(_omw())
    assert tables.false_friends == []
    assert tables.concept_relations == []
