"""Tests for the OMW source adapter (`ingestion.sources.omw`).

Only the pure half (`slugify`, `group_to_records`) is exercised - the ``wn``-backed
`wn_synset_entries` needs a download and the optional ``ingest`` extra.
"""

from dataclasses import dataclass

import pytest

from lang_tools.lexicon.concept_id import CONCEPT_ID_RE
from lang_tools.lexicon.ingestion.sources.omw import OMW_VERSION
from lang_tools.lexicon.ingestion.sources.omw import SOURCE_CILI
from lang_tools.lexicon.ingestion.sources.omw import SOURCE_OMW
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.sources.omw import UnknownOmwLanguageError
from lang_tools.lexicon.ingestion.sources.omw import _ili_id
from lang_tools.lexicon.ingestion.sources.omw import _omw_lexicon
from lang_tools.lexicon.ingestion.sources.omw import group_to_records
from lang_tools.lexicon.ingestion.sources.omw import slugify


def test_slugify_accent_and_punctuation() -> None:
    assert slugify("Ação Penal!") == "acao-penal"
    assert slugify("a/b c d e f") == "a-b-c-d"  # capped at 4 hyphen-words
    assert slugify("   ") == "concept"
    assert slugify("123") == "123"


def test_slug_matches_concept_id_shape() -> None:
    entries = [SynsetEntry("en", "s1", "i123", "a dwelling", ("house",), "n")]
    concepts, _, _, _ = group_to_records(entries)
    assert CONCEPT_ID_RE.match(concepts[0].id)


def test_shared_ili_groups_into_one_cross_lingual_concept() -> None:
    en_def = "a building for living"
    pt_def = "uma construcao para morar"
    entries = [
        SynsetEntry("en", "en-1", "i00001", en_def, ("house",), "n"),
        SynsetEntry("pt", "pt-1", "i00001", pt_def, ("casa",), "n"),
    ]
    concepts, lemmas, senses, _ = group_to_records(entries)
    assert len(concepts) == 1
    assert concepts[0].definitions == {"en": en_def, "pt": pt_def}
    # Two lemmas in two languages, both linked to the one concept.
    assert {lem.text for lem in lemmas} == {"house", "casa"}
    assert {lem.language for lem in lemmas} == {"en", "pt"}
    assert len(senses) == 2
    assert {s.concept_id for s in senses} == {concepts[0].id}


def test_cili_fills_missing_english_gloss_and_tags_cili() -> None:
    # An ILI-backed concept with no English OMW gloss: the CILI English gloss
    # (carried on `ili_definition`) fills the en slot and the concept is tagged
    # cili. Non-English OMW glosses are untouched.
    entries = [
        SynsetEntry(
            "pt", "pt-1", "i7", "uma moradia", ("casa",), "n",
            ili_definition="a building for living",
        ),
    ]
    concepts, _, _, sources = group_to_records(entries)
    assert concepts[0].definitions == {
        "pt": "uma moradia",
        "en": "a building for living",
    }
    assert sources == [SOURCE_CILI]


def test_cili_not_used_when_english_gloss_present() -> None:
    # OMW already has the English gloss, so the ILI fallback is ignored and the
    # concept stays tagged omw.
    entries = [
        SynsetEntry(
            "en", "en-1", "i7", "a building for living", ("house",), "n",
            ili_definition="ignored ili gloss",
        ),
    ]
    concepts, _, _, sources = group_to_records(entries)
    assert concepts[0].definitions == {"en": "a building for living"}
    assert sources == [SOURCE_OMW]


def test_no_ili_stays_monolingual() -> None:
    entries = [
        SynsetEntry("en", "en-1", None, "meaning one", ("foo",), "n"),
        SynsetEntry("pt", "pt-1", None, "significado dois", ("bar",), "n"),
    ]
    concepts, _, _, _ = group_to_records(entries)
    assert len(concepts) == 2  # no shared ILI -> two separate concepts


def test_lemma_and_sense_dedup() -> None:
    # Same form in two synsets that happen to share an ILI -> one lemma, one sense.
    entries = [
        SynsetEntry("en", "en-1", "iX", "sense a", ("bank",), "n"),
        SynsetEntry("en", "en-1b", "iX", "sense a too", ("bank",), "n"),
    ]
    _, lemmas, senses, _ = group_to_records(entries)
    assert len(lemmas) == 1
    assert len(senses) == 1


def test_pos_is_mapped() -> None:
    entries = [
        SynsetEntry("en", "v-1", "iV", "to run", ("run",), "v"),
        SynsetEntry("en", "a-1", "iA", "quick", ("fast",), "s"),
    ]
    _, lemmas, _, _ = group_to_records(entries)
    by_text = {lem.text: lem.part_of_speech for lem in lemmas}
    assert by_text == {"run": "verb", "fast": "adjective"}


@dataclass
class _FakeSynset:
    """A stand-in for a ``wn`` synset exposing only ``.ili`` (no download)."""

    ili: object


def test_ili_id_normalizes_str_obj_and_empty() -> None:
    # wn 1.1.0: .ili is a bare string -> the string *is* the id.
    assert _ili_id(_FakeSynset(ili="i35545")) == "i35545"

    # A future/older wn could return an object exposing .id.
    class _Ili:
        id = "i999"

    assert _ili_id(_FakeSynset(ili=_Ili())) == "i999"
    # Falsy ILI -> None (the "monolingual" signal group_to_records expects).
    assert _ili_id(_FakeSynset(ili="")) is None
    assert _ili_id(_FakeSynset(ili=None)) is None


def test_omw_lexicon_maps_known_and_versions() -> None:
    assert _omw_lexicon("en") == f"omw-en:{OMW_VERSION}"
    assert _omw_lexicon("pt", "1.4") == "omw-pt:1.4"
    # `it` deliberately maps to MultiWordNet, not ItalWordNet (omw-iwn).
    assert _omw_lexicon("it") == f"omw-it:{OMW_VERSION}"


def test_omw_lexicon_unknown_language_raises() -> None:
    with pytest.raises(UnknownOmwLanguageError):
        _omw_lexicon("xx")


def test_records_are_sorted_by_id() -> None:
    entries = [
        SynsetEntry("en", "s1", "i1", "d1", ("zebra",), "n"),
        SynsetEntry("en", "s2", "i2", "d2", ("apple",), "n"),
    ]
    concepts, lemmas, senses, _ = group_to_records(entries)
    assert [c.id for c in concepts] == sorted(c.id for c in concepts)
    assert [lem.id for lem in lemmas] == sorted(lem.id for lem in lemmas)
    assert [s.id for s in senses] == sorted(s.id for s in senses)
