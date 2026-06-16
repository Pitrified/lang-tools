"""Tests for the OMW source adapter (`ingestion.sources.omw`).

Only the pure half (`slugify`, `group_to_records`) is exercised - the ``wn``-backed
`wn_synset_entries` needs a download and the optional ``ingest`` extra.
"""

from lang_tools.lexicon.concept_id import CONCEPT_ID_RE
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.sources.omw import group_to_records
from lang_tools.lexicon.ingestion.sources.omw import slugify


def test_slugify_accent_and_punctuation() -> None:
    assert slugify("Ação Penal!") == "acao-penal"
    assert slugify("a/b c d e f") == "a-b-c-d"  # capped at 4 hyphen-words
    assert slugify("   ") == "concept"
    assert slugify("123") == "123"


def test_slug_matches_concept_id_shape() -> None:
    entries = [SynsetEntry("en", "s1", "i123", "a dwelling", ("house",), "n")]
    concepts, _, _ = group_to_records(entries)
    assert CONCEPT_ID_RE.match(concepts[0].id)


def test_shared_ili_groups_into_one_cross_lingual_concept() -> None:
    en_def = "a building for living"
    pt_def = "uma construcao para morar"
    entries = [
        SynsetEntry("en", "en-1", "i00001", en_def, ("house",), "n"),
        SynsetEntry("pt", "pt-1", "i00001", pt_def, ("casa",), "n"),
    ]
    concepts, lemmas, senses = group_to_records(entries)
    assert len(concepts) == 1
    assert concepts[0].definitions == {"en": en_def, "pt": pt_def}
    # Two lemmas in two languages, both linked to the one concept.
    assert {lem.text for lem in lemmas} == {"house", "casa"}
    assert {lem.language for lem in lemmas} == {"en", "pt"}
    assert len(senses) == 2
    assert {s.concept_id for s in senses} == {concepts[0].id}


def test_no_ili_stays_monolingual() -> None:
    entries = [
        SynsetEntry("en", "en-1", None, "meaning one", ("foo",), "n"),
        SynsetEntry("pt", "pt-1", None, "significado dois", ("bar",), "n"),
    ]
    concepts, _, _ = group_to_records(entries)
    assert len(concepts) == 2  # no shared ILI -> two separate concepts


def test_lemma_and_sense_dedup() -> None:
    # Same form in two synsets that happen to share an ILI -> one lemma, one sense.
    entries = [
        SynsetEntry("en", "en-1", "iX", "sense a", ("bank",), "n"),
        SynsetEntry("en", "en-1b", "iX", "sense a too", ("bank",), "n"),
    ]
    _, lemmas, senses = group_to_records(entries)
    assert len(lemmas) == 1
    assert len(senses) == 1


def test_pos_is_mapped() -> None:
    entries = [
        SynsetEntry("en", "v-1", "iV", "to run", ("run",), "v"),
        SynsetEntry("en", "a-1", "iA", "quick", ("fast",), "s"),
    ]
    _, lemmas, _ = group_to_records(entries)
    by_text = {lem.text: lem.part_of_speech for lem in lemmas}
    assert by_text == {"run": "verb", "fast": "adjective"}


def test_records_are_sorted_by_id() -> None:
    entries = [
        SynsetEntry("en", "s1", "i1", "d1", ("zebra",), "n"),
        SynsetEntry("en", "s2", "i2", "d2", ("apple",), "n"),
    ]
    concepts, lemmas, senses = group_to_records(entries)
    assert [c.id for c in concepts] == sorted(c.id for c in concepts)
    assert [lem.id for lem in lemmas] == sorted(lem.id for lem in lemmas)
    assert [s.id for s in senses] == sorted(s.id for s in senses)
