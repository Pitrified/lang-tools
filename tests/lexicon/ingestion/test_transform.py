"""Tests for the transform stage (`ingestion.transform`)."""

from collections.abc import Iterator

from lang_tools.lexicon.ingestion.sources.kaikki import KaikkiEntry
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.transform import SOURCE_KAIKKI
from lang_tools.lexicon.ingestion.transform import SOURCE_OMW
from lang_tools.lexicon.ingestion.transform import transform
from lang_tools.lexicon.lemma import LemmaExample


def _omw() -> list[SynsetEntry]:
    return [
        SynsetEntry("en", "en-1", "i1", "a building for living", ("house",), "n"),
        # pt synset shares the ILI but has no gloss -> a hole kaikki can fill.
        SynsetEntry("pt", "pt-1", "i1", None, ("casa",), "n"),
    ]


def test_pure_omw_tags_everything_omw() -> None:
    tables = transform(_omw())
    assert set(tables.concept_sources) == {SOURCE_OMW}
    assert set(tables.lemma_sources) == {SOURCE_OMW}
    assert set(tables.sense_sources) == {SOURCE_OMW}
    # The pt gloss stays empty without enrichment.
    assert tables.concepts[0].definitions == {"en": "a building for living"}


def test_kaikki_fills_sparse_definition_and_retags_concept() -> None:
    kaikki = [KaikkiEntry(text="casa", language="pt", definitions=["uma moradia"])]
    tables = transform(_omw(), kaikki)
    assert tables.concepts[0].definitions == {
        "en": "a building for living",
        "pt": "uma moradia",
    }
    # The concept now carries kaikki (CC-BY-SA) content -> tagged kaikki.
    assert tables.concept_sources == [SOURCE_KAIKKI]


def test_kaikki_attaches_examples_and_retags_lemma() -> None:
    kaikki = [
        KaikkiEntry(
            text="casa",
            language="pt",
            examples=[LemmaExample(sentence="a casa", translation="the house")],
        ),
    ]
    tables = transform(_omw(), kaikki)
    casa = next(lem for lem in tables.lemmas if lem.text == "casa")
    house = next(lem for lem in tables.lemmas if lem.text == "house")
    idx_casa = tables.lemmas.index(casa)
    idx_house = tables.lemmas.index(house)
    assert casa.examples[0].sentence == "a casa"
    assert SOURCE_KAIKKI in casa.sources
    assert tables.lemma_sources[idx_casa] == SOURCE_KAIKKI
    # The un-enriched lemma stays omw.
    assert tables.lemma_sources[idx_house] == SOURCE_OMW


def test_no_kaikki_match_leaves_rows_untouched() -> None:
    kaikki = [KaikkiEntry(text="unrelated", language="pt", definitions=["x"])]
    tables = transform(_omw(), kaikki)
    assert tables.concept_sources == [SOURCE_OMW]
    assert set(tables.lemma_sources) == {SOURCE_OMW}


def test_relation_tables_stay_empty() -> None:
    tables = transform(_omw())
    assert tables.false_friends == []
    assert tables.concept_relations == []


def test_kaikki_is_streamed_filtered_and_single_pass() -> None:
    # Mostly non-matching entries (absent from the OMW backbone) interleaved with
    # one match; wrap them in a counting generator that can only be walked once.
    yielded = 0

    def kaikki_stream() -> Iterator[KaikkiEntry]:
        nonlocal yielded
        for entry in [
            KaikkiEntry(text="absent-1", language="pt", definitions=["x"]),
            KaikkiEntry(text="casa", language="pt", definitions=["uma moradia"]),
            KaikkiEntry(text="absent-2", language="pt", definitions=["y"]),
        ]:
            yielded += 1
            yield entry

    tables = transform(_omw(), kaikki_stream())

    # (a) Only the matching entry is retained; the rest are dropped immediately.
    assert tables.concepts[0].definitions["pt"] == "uma moradia"
    assert tables.concept_sources == [SOURCE_KAIKKI]
    # (b) The iterator was consumed exactly once, in full (streamed, not listed).
    assert yielded == 3
