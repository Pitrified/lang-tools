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
from lang_tools.lexicon.ingestion.sources.omw import is_malformed_form
from lang_tools.lexicon.ingestion.sources.omw import slugify


def test_slugify_accent_and_punctuation() -> None:
    assert slugify("Ação Penal!") == "acao-penal"
    assert slugify("a/b c d e f") == "a-b-c-d"  # capped at 4 hyphen-words
    assert slugify("   ") == "concept"
    assert slugify("123") == "123"


def test_slug_matches_concept_id_shape() -> None:
    entries = [SynsetEntry("en", "s1", "i123", "a dwelling", ("house",), "n")]
    concepts, _, _, _, _ = group_to_records(entries)
    assert CONCEPT_ID_RE.match(concepts[0].id)


def test_shared_ili_groups_into_one_cross_lingual_concept() -> None:
    en_def = "a building for living"
    pt_def = "uma construcao para morar"
    entries = [
        SynsetEntry("en", "en-1", "i00001", en_def, ("house",), "n"),
        SynsetEntry("pt", "pt-1", "i00001", pt_def, ("casa",), "n"),
    ]
    concepts, lemmas, senses, _, _ = group_to_records(entries)
    assert len(concepts) == 1
    assert concepts[0].definitions == {"en": en_def, "pt": pt_def}
    # Two lemmas in two languages, both linked to the one concept.
    assert {lem.text for lem in lemmas} == {"house", "casa"}
    assert {lem.language for lem in lemmas} == {"en", "pt"}
    assert len(senses) == 2
    assert {s.concept_id for s in senses} == {concepts[0].id}


def test_cili_fills_missing_english_gloss_and_tags_cili() -> None:
    # An ILI-backed concept with no English OMW gloss: the CILI gloss map (keyed
    # by ILI id) fills the en slot and the concept is tagged cili. Non-English
    # OMW glosses are untouched.
    entries = [SynsetEntry("pt", "pt-1", "i7", "uma moradia", ("casa",), "n")]
    concepts, _, _, sources, _ = group_to_records(
        entries,
        {"i7": "a building for living"},
    )
    assert concepts[0].definitions == {
        "pt": "uma moradia",
        "en": "a building for living",
    }
    assert sources == [SOURCE_CILI]


def test_cili_not_used_when_english_gloss_present() -> None:
    # OMW already has the English gloss, so the ILI fallback is ignored and the
    # concept stays tagged omw.
    entries = [SynsetEntry("en", "en-1", "i7", "a dwelling", ("house",), "n")]
    concepts, _, _, sources, _ = group_to_records(entries, {"i7": "ignored"})
    assert concepts[0].definitions == {"en": "a dwelling"}
    assert sources == [SOURCE_OMW]


def test_cili_skipped_for_ili_orphan() -> None:
    # No ILI -> grouped by synset id -> the CILI map cannot key it, so the concept
    # stays omw with no English gloss even when the map is non-empty.
    entries = [SynsetEntry("pt", "pt-1", None, "uma moradia", ("casa",), "n")]
    concepts, _, _, sources, _ = group_to_records(
        entries,
        {"i7": "a building for living"},
    )
    assert "en" not in concepts[0].definitions
    assert sources == [SOURCE_OMW]


def test_no_cili_map_disables_fallback() -> None:
    # Default (no map): a missing English gloss stays missing and tagged omw.
    entries = [SynsetEntry("pt", "pt-1", "i7", "uma moradia", ("casa",), "n")]
    concepts, _, _, sources, _ = group_to_records(entries)
    assert "en" not in concepts[0].definitions
    assert sources == [SOURCE_OMW]


def test_no_ili_stays_monolingual() -> None:
    entries = [
        SynsetEntry("en", "en-1", None, "meaning one", ("foo",), "n"),
        SynsetEntry("pt", "pt-1", None, "significado dois", ("bar",), "n"),
    ]
    concepts, _, _, _, _ = group_to_records(entries)
    assert len(concepts) == 2  # no shared ILI -> two separate concepts


def test_lemma_and_sense_dedup() -> None:
    # Same form in two synsets that happen to share an ILI -> one lemma, one sense.
    entries = [
        SynsetEntry("en", "en-1", "iX", "sense a", ("bank",), "n"),
        SynsetEntry("en", "en-1b", "iX", "sense a too", ("bank",), "n"),
    ]
    _, lemmas, senses, _, _ = group_to_records(entries)
    assert len(lemmas) == 1
    assert len(senses) == 1


def test_pos_is_mapped() -> None:
    entries = [
        SynsetEntry("en", "v-1", "iV", "to run", ("run",), "v"),
        SynsetEntry("en", "a-1", "iA", "quick", ("fast",), "s"),
    ]
    _, lemmas, _, _, _ = group_to_records(entries)
    by_text = {lem.text: lem.part_of_speech for lem in lemmas}
    assert by_text == {"run": "verb", "fast": "adjective"}


def test_unique_slug_stays_tier0() -> None:
    # No collision -> the lexfile is not appended (tier 0 wins).
    entries = [
        SynsetEntry(
            "en", "s1", "i1", "a dwelling", ("house",), "n", lexfile="noun.artifact",
        ),
    ]
    concepts, _, _, _, _ = group_to_records(entries)
    assert concepts[0].id.startswith("c__house__")


def test_colliding_slugs_get_lexfile_discriminant() -> None:
    # Two concepts sharing the tier-0 slug `cut` split on their lexfiles.
    entries = [
        SynsetEntry(
            "en", "s1", "i1", "separate with an edge", ("cut",), "v",
            lexfile="verb.contact",
        ),
        SynsetEntry(
            "en", "s2", "i2", "the act of cutting", ("cut",), "n",
            lexfile="noun.act",
        ),
    ]
    concepts, _, _, _, _ = group_to_records(entries)
    slugs = {c.id.split("__")[1] for c in concepts}
    assert slugs == {"cut-verb-contact", "cut-noun-act"}


def test_same_lexfile_collision_keeps_tier1_slug() -> None:
    # True polysemy (same slug, same lexfile): both keep the tier-1 slug and the
    # hash disambiguates; the qualifier tier is deferred to phase 8.
    entries = [
        SynsetEntry(
            "en", "s1", "i1", "person one", ("aaron",), "n", lexfile="noun.person",
        ),
        SynsetEntry(
            "en", "s2", "i2", "person two", ("aaron",), "n", lexfile="noun.person",
        ),
    ]
    concepts, _, _, _, _ = group_to_records(entries)
    assert [c.id.split("__")[1] for c in concepts] == [
        "aaron-noun-person",
        "aaron-noun-person",
    ]
    assert len({c.id for c in concepts}) == 2


def test_generic_concept_fallback_gets_lexfile_even_when_unique() -> None:
    # No lemma, no definition -> tier-0 slug is the generic `concept`; the
    # lexfile is appended even without a collision so no bare `concept` survives.
    entries = [SynsetEntry("en", "s1", "i1", None, (), "n", lexfile="noun.tops")]
    concepts, _, _, _, _ = group_to_records(entries)
    assert concepts[0].id.startswith("c__concept-noun-tops__")


def test_colliding_slug_without_lexfile_keeps_tier0() -> None:
    # A collision with no lexfile anywhere has no discriminant to append.
    entries = [
        SynsetEntry("en", "s1", "i1", "d1", ("cut",), "n"),
        SynsetEntry("en", "s2", "i2", "d2", ("cut",), "v"),
    ]
    concepts, _, _, _, _ = group_to_records(entries)
    assert all(c.id.split("__")[1] == "cut" for c in concepts)


def test_is_malformed_form_flags_wiki_anchors() -> None:
    assert is_malformed_form("Grotte#Culture")
    assert is_malformed_form("jeûne#je.c3.bbne politique")  # lowercase .c3.
    assert is_malformed_form("Radiateur#.C3.89changeur solide.2Fair")
    assert not is_malformed_form("monoxyde de carbone")


def test_malformed_forms_dropped_with_their_senses() -> None:
    # The wiki-anchor member never becomes a lemma or a sense; the clean member
    # still attaches, so the concept is not orphaned.
    entries = [
        SynsetEntry(
            "fr", "fr-1", "i1", "une grotte", ("grotte", "Grotte#Culture"), "n",
        ),
    ]
    concepts, lemmas, senses, _, _ = group_to_records(entries)
    assert [lem.text for lem in lemmas] == ["grotte"]
    assert len(senses) == 1
    assert len(concepts) == 1


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
    concepts, lemmas, senses, _, _ = group_to_records(entries)
    assert [c.id for c in concepts] == sorted(c.id for c in concepts)
    assert [lem.id for lem in lemmas] == sorted(lem.id for lem in lemmas)
    assert [s.id for s in senses] == sorted(s.id for s in senses)


def test_lexfile_prefers_english_synset_and_propagates() -> None:
    # lexfile is carried on the English synset; the pt member of the same ILI
    # concept has none, so the concept takes the English one (concept-level).
    entries = [
        SynsetEntry("pt", "pt-1", "iL", "uma moradia", ("casa",), "n"),
        SynsetEntry(
            "en", "en-1", "iL", "a dwelling", ("house",), "n", lexfile="noun.artifact",
        ),
    ]
    concepts, _, _, _, _ = group_to_records(entries)
    assert concepts[0].lexfile == "noun.artifact"


def test_examples_are_concept_level_per_language_sorted_unique() -> None:
    entries = [
        SynsetEntry(
            "en", "en-1", "iE", "a dwelling", ("house",), "n",
            examples=("they built a house", "a house", "a house"),
        ),
        SynsetEntry(
            "pt", "pt-1", "iE", "uma moradia", ("casa",), "n",
            examples=("uma casa",),
        ),
    ]
    concepts, _, _, _, _ = group_to_records(entries)
    # Duplicates dropped, each language sorted; both languages present.
    assert concepts[0].examples == {
        "en": ["a house", "they built a house"],
        "pt": ["uma casa"],
    }


def test_hypernym_links_become_directional_concept_relations() -> None:
    # dog (en-1) -> animal (en-2). The child is concept_id_a, the parent _b.
    entries = [
        SynsetEntry(
            "en", "en-1", "i1", "a dog", ("dog",), "n", hypernyms=("en-2",),
        ),
        SynsetEntry("en", "en-2", "i2", "an animal", ("animal",), "n"),
    ]
    concepts, _, _, _, relations = group_to_records(entries)
    by_def = {next(iter(c.definitions.values())): c.id for c in concepts}
    assert len(relations) == 1
    edge = relations[0]
    assert edge.relation_type == "hypernym"
    assert edge.concept_id_a == by_def["a dog"]
    assert edge.concept_id_b == by_def["an animal"]


def test_hypernym_edges_dedupe_and_drop_dangling() -> None:
    # en-1 points to en-2 (resolves) and to en-missing (dangling, dropped).
    # A second synset of the same ILI repeats the en-2 link -> one deduped edge.
    entries = [
        SynsetEntry(
            "en", "en-1", "iA", "a dog", ("dog",), "n",
            hypernyms=("en-2", "en-missing"),
        ),
        SynsetEntry(
            "en", "en-1b", "iA", "a dog too", ("hound",), "n", hypernyms=("en-2",),
        ),
        SynsetEntry("en", "en-2", "iB", "an animal", ("animal",), "n"),
    ]
    _, _, _, _, relations = group_to_records(entries)
    assert len(relations) == 1  # deduped; the dangling en-missing edge is dropped
