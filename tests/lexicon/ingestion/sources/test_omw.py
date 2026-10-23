"""Tests for the OMW source adapter (`ingestion.sources.omw`).

Only the pure half (`slugify`, `group_to_records`) is exercised - the ``wn``-backed
`wn_synset_entries` needs a download and the optional ``ingest`` extra.
"""

from dataclasses import dataclass

import pytest

from lang_tools.lexicon.concept_id import CONCEPT_ID_RE
from lang_tools.lexicon.ingestion.sources.omw import OMW_VERSION
from lang_tools.lexicon.ingestion.sources.omw import SOURCE_CILI
from lang_tools.lexicon.ingestion.sources.omw import SOURCE_DERIVED
from lang_tools.lexicon.ingestion.sources.omw import SOURCE_OMW
from lang_tools.lexicon.ingestion.sources.omw import MemberCountMismatchError
from lang_tools.lexicon.ingestion.sources.omw import SenseLink
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.sources.omw import UnknownOmwLanguageError
from lang_tools.lexicon.ingestion.sources.omw import _ili_id
from lang_tools.lexicon.ingestion.sources.omw import _omw_lexicon
from lang_tools.lexicon.ingestion.sources.omw import group_to_records
from lang_tools.lexicon.ingestion.sources.omw import is_malformed_form
from lang_tools.lexicon.ingestion.sources.omw import member_forms
from lang_tools.lexicon.ingestion.sources.omw import slugify
from lang_tools.lexicon.ingestion.sources.omw import unescape_form


def test_slugify_accent_and_punctuation() -> None:
    assert slugify("Ação Penal!") == "acao-penal"
    assert slugify("a/b c d e f") == "a-b-c-d"  # capped at 4 hyphen-words
    assert slugify("   ") == "concept"
    assert slugify("123") == "123"


def test_slug_matches_concept_id_shape() -> None:
    entries = [SynsetEntry("en", "s1", "i123", "a dwelling", ("house",), pos="n")]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    assert CONCEPT_ID_RE.match(concepts[0].id)


def test_shared_ili_groups_into_one_cross_lingual_concept() -> None:
    en_def = "a building for living"
    pt_def = "uma construcao para morar"
    entries = [
        SynsetEntry("en", "en-1", "i00001", en_def, ("house",), pos="n"),
        SynsetEntry("pt", "pt-1", "i00001", pt_def, ("casa",), pos="n"),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    lemmas = grouped.lemmas
    senses = grouped.senses
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
    entries = [SynsetEntry("pt", "pt-1", "i7", "uma moradia", ("casa",), pos="n")]
    grouped = group_to_records(
        entries,
        {"i7": "a building for living"},
    )
    concepts = grouped.concepts
    sources = grouped.concept_sources
    assert concepts[0].definitions == {
        "pt": "uma moradia",
        "en": "a building for living",
    }
    assert sources == [SOURCE_CILI]


def test_cili_not_used_when_english_gloss_present() -> None:
    # OMW already has the English gloss, so the ILI fallback is ignored and the
    # concept stays tagged omw.
    entries = [SynsetEntry("en", "en-1", "i7", "a dwelling", ("house",), pos="n")]
    grouped = group_to_records(entries, {"i7": "ignored"})
    concepts = grouped.concepts
    sources = grouped.concept_sources
    assert concepts[0].definitions == {"en": "a dwelling"}
    assert sources == [SOURCE_OMW]


def test_cili_skipped_for_ili_orphan() -> None:
    # No ILI -> grouped by synset id -> the CILI map cannot key it, so the concept
    # stays omw with no English gloss even when the map is non-empty.
    entries = [SynsetEntry("pt", "pt-1", None, "uma moradia", ("casa",), pos="n")]
    grouped = group_to_records(
        entries,
        {"i7": "a building for living"},
    )
    concepts = grouped.concepts
    sources = grouped.concept_sources
    assert "en" not in concepts[0].definitions
    assert sources == [SOURCE_OMW]


def test_no_cili_map_disables_fallback() -> None:
    # Default (no map): a missing English gloss stays missing and tagged omw.
    entries = [SynsetEntry("pt", "pt-1", "i7", "uma moradia", ("casa",), pos="n")]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    sources = grouped.concept_sources
    assert "en" not in concepts[0].definitions
    assert sources == [SOURCE_OMW]


def test_no_ili_stays_monolingual() -> None:
    entries = [
        SynsetEntry("en", "en-1", None, "meaning one", ("foo",), pos="n"),
        SynsetEntry("pt", "pt-1", None, "significado dois", ("bar",), pos="n"),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    assert len(concepts) == 2  # no shared ILI -> two separate concepts


def test_lemma_and_sense_dedup() -> None:
    # Same form in two synsets that happen to share an ILI -> one lemma, one sense.
    entries = [
        SynsetEntry("en", "en-1", "iX", "sense a", ("bank",), pos="n"),
        SynsetEntry("en", "en-1b", "iX", "sense a too", ("bank",), pos="n"),
    ]
    grouped = group_to_records(entries)
    lemmas = grouped.lemmas
    senses = grouped.senses
    assert len(lemmas) == 1
    assert len(senses) == 1


def test_pos_is_mapped() -> None:
    entries = [
        SynsetEntry("en", "v-1", "iV", "to run", ("run",), pos="v"),
        SynsetEntry("en", "a-1", "iA", "quick", ("fast",), pos="s"),
    ]
    grouped = group_to_records(entries)
    lemmas = grouped.lemmas
    by_text = {lem.text: lem.part_of_speech for lem in lemmas}
    assert by_text == {"run": "verb", "fast": "adjective"}


def test_unique_slug_stays_tier0() -> None:
    # No collision -> the lexfile is not appended (tier 0 wins).
    entries = [
        SynsetEntry(
            "en",
            "s1",
            "i1",
            "a dwelling",
            ("house",),
            pos="n",
            lexfile="noun.artifact",
        ),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    assert concepts[0].id.startswith("c__house__")


def test_colliding_slugs_get_lexfile_discriminant() -> None:
    # Two concepts sharing the tier-0 slug `cut` split on their lexfiles.
    entries = [
        SynsetEntry(
            "en",
            "s1",
            "i1",
            "separate with an edge",
            ("cut",),
            pos="v",
            lexfile="verb.contact",
        ),
        SynsetEntry(
            "en",
            "s2",
            "i2",
            "the act of cutting",
            ("cut",),
            pos="n",
            lexfile="noun.act",
        ),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    slugs = {c.id.split("__")[1] for c in concepts}
    assert slugs == {"cut-verb-contact", "cut-noun-act"}


def test_same_lexfile_collision_keeps_tier1_slug() -> None:
    # True polysemy (same slug, same lexfile): both keep the tier-1 slug and the
    # hash disambiguates; the qualifier tier is deferred to phase 8.
    entries = [
        SynsetEntry(
            "en",
            "s1",
            "i1",
            "person one",
            ("aaron",),
            pos="n",
            lexfile="noun.person",
        ),
        SynsetEntry(
            "en",
            "s2",
            "i2",
            "person two",
            ("aaron",),
            pos="n",
            lexfile="noun.person",
        ),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    assert [c.id.split("__")[1] for c in concepts] == [
        "aaron-noun-person",
        "aaron-noun-person",
    ]
    assert len({c.id for c in concepts}) == 2


def test_generic_concept_fallback_gets_lexfile_even_when_unique() -> None:
    # No lemma, no definition -> tier-0 slug is the generic `concept`; the
    # lexfile is appended even without a collision so no bare `concept` survives.
    entries = [SynsetEntry("en", "s1", "i1", None, (), pos="n", lexfile="noun.tops")]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    assert concepts[0].id.startswith("c__concept-noun-tops__")


def test_colliding_slug_without_lexfile_keeps_tier0() -> None:
    # A collision with no lexfile anywhere has no discriminant to append.
    entries = [
        SynsetEntry("en", "s1", "i1", "d1", ("cut",), pos="n"),
        SynsetEntry("en", "s2", "i2", "d2", ("cut",), pos="v"),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    assert all(c.id.split("__")[1] == "cut" for c in concepts)


def test_is_malformed_form_flags_wiki_anchors() -> None:
    assert is_malformed_form("Grotte#Culture")
    assert is_malformed_form("jeûne#je.c3.bbne politique")  # lowercase .c3.
    assert is_malformed_form("Radiateur#.C3.89changeur solide.2Fair")
    assert not is_malformed_form("monoxyde de carbone")


def test_is_malformed_form_flags_markup_and_placeholders() -> None:
    # 5.57: leftover markup, once unescaped, and MultiWordNet's gap markers.
    assert is_malformed_form(unescape_form("Milan &lt;!--gender?--&gt;"))
    assert is_malformed_form(unescape_form("vitamine B&lt;sub&gt;6&lt;/sub&gt;"))
    assert is_malformed_form("<HTML>")
    assert is_malformed_form("GAP!")
    assert is_malformed_form("pseudogap!")
    # Placeholders match exactly, so these real lemmas survive.
    assert not is_malformed_form("gap")
    assert not is_malformed_form("Gap")
    assert not is_malformed_form("stopgap")


def test_unescape_form_repairs_recoverable_forms() -> None:
    # Entities that resolve to a real word are repaired, not dropped.
    repaired = unescape_form("fr&amp;eacute;n&amp;eacute;sie")
    assert repaired == "frénésie"
    assert not is_malformed_form(repaired)
    assert unescape_form("Parc national de Sequoia &amp; Kings Canyon") == (
        "Parc national de Sequoia & Kings Canyon"
    )
    assert unescape_form("monoxyde de carbone") == "monoxyde de carbone"


def test_placeholder_member_dropped_with_its_senses() -> None:
    # A GAP! member never becomes a lemma or a sense; the en member still
    # attaches, so the concept keeps a member.
    entries = [
        SynsetEntry(
            language="en",
            synset_id="s1",
            ili="i1",
            definition="a gloss",
            lemmas=("mind",),
            pos="n",
        ),
        SynsetEntry(
            language="it",
            synset_id="s1i",
            ili="i1",
            definition=None,
            lemmas=("GAP!",),
            pos="n",
        ),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    lemmas = grouped.lemmas
    senses = grouped.senses
    assert len(concepts) == 1
    assert [lemma.text for lemma in lemmas] == ["mind"]
    assert len(senses) == 1


def test_malformed_forms_dropped_with_their_senses() -> None:
    # The wiki-anchor member never becomes a lemma or a sense; the clean member
    # still attaches, so the concept is not orphaned.
    entries = [
        SynsetEntry(
            "fr",
            "fr-1",
            "i1",
            "une grotte",
            ("grotte", "Grotte#Culture"),
            pos="n",
        ),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    lemmas = grouped.lemmas
    senses = grouped.senses
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
        SynsetEntry("en", "s1", "i1", "d1", ("zebra",), pos="n"),
        SynsetEntry("en", "s2", "i2", "d2", ("apple",), pos="n"),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    lemmas = grouped.lemmas
    senses = grouped.senses
    assert [c.id for c in concepts] == sorted(c.id for c in concepts)
    assert [lem.id for lem in lemmas] == sorted(lem.id for lem in lemmas)
    assert [s.id for s in senses] == sorted(s.id for s in senses)


def test_lexfile_prefers_english_synset_and_propagates() -> None:
    # lexfile is carried on the English synset; the pt member of the same ILI
    # concept has none, so the concept takes the English one (concept-level).
    entries = [
        SynsetEntry("pt", "pt-1", "iL", "uma moradia", ("casa",), pos="n"),
        SynsetEntry(
            "en",
            "en-1",
            "iL",
            "a dwelling",
            ("house",),
            pos="n",
            lexfile="noun.artifact",
        ),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    assert concepts[0].lexfile == "noun.artifact"


def test_examples_are_concept_level_per_language_sorted_unique() -> None:
    entries = [
        SynsetEntry(
            "en",
            "en-1",
            "iE",
            "a dwelling",
            ("house",),
            pos="n",
            examples=("they built a house", "a house", "a house"),
        ),
        SynsetEntry(
            "pt",
            "pt-1",
            "iE",
            "uma moradia",
            ("casa",),
            pos="n",
            examples=("uma casa",),
        ),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    # Duplicates dropped, each language sorted; both languages present.
    assert concepts[0].examples == {
        "en": ["a house", "they built a house"],
        "pt": ["uma casa"],
    }


def test_hypernym_links_become_directional_concept_relations() -> None:
    # dog (en-1) -> animal (en-2). The child is concept_id_a, the parent _b.
    entries = [
        SynsetEntry(
            "en",
            "en-1",
            "i1",
            "a dog",
            ("dog",),
            pos="n",
            relations={"hypernym": ("en-2",)},
        ),
        SynsetEntry("en", "en-2", "i2", "an animal", ("animal",), pos="n"),
    ]
    grouped = group_to_records(entries)
    concepts = grouped.concepts
    relations = grouped.relations
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
            "en",
            "en-1",
            "iA",
            "a dog",
            ("dog",),
            pos="n",
            relations={"hypernym": ("en-2", "en-missing")},
        ),
        SynsetEntry(
            "en",
            "en-1b",
            "iA",
            "a dog too",
            ("hound",),
            pos="n",
            relations={"hypernym": ("en-2",)},
        ),
        SynsetEntry("en", "en-2", "iB", "an animal", ("animal",), pos="n"),
    ]
    grouped = group_to_records(entries)
    relations = grouped.relations
    assert len(relations) == 1  # deduped; the dangling en-missing edge is dropped


def _cid(grouped, gloss: str) -> str:  # noqa: ANN001 - GroupedRecords
    return next(c.id for c in grouped.concepts if gloss in c.definitions.values())


def _edges(grouped) -> set[tuple[str, str, str]]:  # noqa: ANN001 - GroupedRecords
    return {
        (rel.concept_id_a, rel.concept_id_b, rel.relation_type)
        for rel in grouped.relations
    }


def test_hyponym_only_link_is_stored_as_a_reversed_hypernym() -> None:
    # pt states animal -> dog only as hyponym; reading it recovers the dog -> animal
    # edge the hypernym-only build dropped (phase 7 Decision 1).
    entries = [
        SynsetEntry("pt", "pt-1", "i1", "um cao", ("cão",), pos="n"),
        SynsetEntry(
            "pt",
            "pt-2",
            "i2",
            "um animal",
            ("animal",),
            pos="n",
            relations={"hyponym": ("pt-1",)},
        ),
    ]
    grouped = group_to_records(entries)
    dog, animal = _cid(grouped, "um cao"), _cid(grouped, "um animal")
    assert _edges(grouped) == {(dog, animal, "hypernym")}


def test_both_halves_of_an_inverse_pair_dedupe_to_one_edge() -> None:
    entries = [
        SynsetEntry(
            "en",
            "en-1",
            "i1",
            "a car",
            ("car",),
            pos="n",
            relations={"mero_part": ("en-2",)},
        ),
        SynsetEntry(
            "en",
            "en-2",
            "i2",
            "a pedal",
            ("accelerator",),
            pos="n",
            relations={"holo_part": ("en-1",)},
        ),
    ]
    grouped = group_to_records(entries)
    car, pedal = _cid(grouped, "a car"), _cid(grouped, "a pedal")
    # a is the whole, b the part, whichever half stated it.
    assert _edges(grouped) == {(car, pedal, "mero_part")}


def test_edge_stated_both_ways_keeps_the_better_supported_direction() -> None:
    # The WordNet 3.0 restrain/inhibit cycle: restrain lists inhibit as both its
    # hypernym and its hyponym, inhibit lists restrain as a hyponym. restrain ->
    # inhibit is stated twice, the reverse once.
    entries = [
        SynsetEntry(
            "en",
            "en-1",
            "i1",
            "keep in check",
            ("restrain",),
            pos="v",
            relations={"hypernym": ("en-2",), "hyponym": ("en-2",)},
        ),
        SynsetEntry(
            "en",
            "en-2",
            "i2",
            "control and refrain",
            ("inhibit",),
            pos="v",
            relations={"hyponym": ("en-1",)},
        ),
    ]
    grouped = group_to_records(entries)
    restrain = _cid(grouped, "keep in check")
    inhibit = _cid(grouped, "control and refrain")
    assert _edges(grouped) == {(restrain, inhibit, "hypernym")}


def test_edge_stated_both_ways_equally_is_dropped() -> None:
    entries = [
        SynsetEntry(
            "en",
            "en-1",
            "i1",
            "first",
            ("one",),
            pos="n",
            relations={"hypernym": ("en-2",)},
        ),
        SynsetEntry(
            "en",
            "en-2",
            "i2",
            "second",
            ("two",),
            pos="n",
            relations={"hypernym": ("en-1",)},
        ),
    ]
    assert group_to_records(entries).relations == []


def test_unmirrored_symmetric_links_get_canonical_order() -> None:
    entries = [
        SynsetEntry(
            "it",
            "it-1",
            "i1",
            "caldo",
            ("caldo",),
            pos="a",
            relations={"similar": ("it-2",)},
        ),
        SynsetEntry(
            "it",
            "it-2",
            "i2",
            "bollente",
            ("bollente",),
            pos="a",
            relations={"similar": ("it-1",)},
        ),
        SynsetEntry(
            "it",
            "it-3",
            "i3",
            "tiepido",
            ("tiepido",),
            pos="a",
            relations={"similar": ("it-1",)},  # unmirrored: it-1 never names it-3
        ),
    ]
    grouped = group_to_records(entries)
    hot, boiling, warm = (_cid(grouped, g) for g in ("caldo", "bollente", "tiepido"))
    expected = {
        (*sorted((hot, boiling)), "similar"),
        (*sorted((hot, warm)), "similar"),
    }
    assert _edges(grouped) == expected


def test_unlisted_relation_names_are_not_stored() -> None:
    entries = [
        SynsetEntry(
            "en",
            "en-1",
            "i1",
            "a tackle",
            ("tackle",),
            pos="n",
            relations={"domain_topic": ("en-2",), "entails": ("en-2",)},
        ),
        SynsetEntry("en", "en-2", "i2", "football", ("football",), pos="n"),
    ]
    grouped = group_to_records(entries)
    assert {rel for _, _, rel in _edges(grouped)} == {"entails"}
    assert grouped.relation_sources == [SOURCE_OMW]


def test_sense_antonym_is_stored_and_derived_to_concept_level() -> None:
    # English says hot (in i1) is the antonym of cold (in i2); Portuguese shares
    # the two concepts but has no sense relations. The derived concept edge is what
    # lets "quente" reach "frio".
    entries = [
        SynsetEntry(
            "en",
            "en-1",
            "i1",
            "of high temperature",
            ("hot",),
            pos="a",
            sense_links=(SenseLink("hot", "antonym", "en-2", "cold"),),
        ),
        SynsetEntry(
            "en",
            "en-2",
            "i2",
            "of low temperature",
            ("cold",),
            pos="a",
            sense_links=(SenseLink("cold", "antonym", "en-1", "hot"),),
        ),
        SynsetEntry("pt", "pt-1", "i1", None, ("quente",), pos="a"),
        SynsetEntry("pt", "pt-2", "i2", None, ("frio",), pos="a"),
    ]
    grouped = group_to_records(entries)
    hot = _cid(grouped, "of high temperature")
    cold = _cid(grouped, "of low temperature")
    assert _edges(grouped) == {(*sorted((hot, cold)), "antonym")}
    assert grouped.relation_sources == [SOURCE_DERIVED]
    # One sense edge (the mirrored link dedupes), between the two English senses.
    assert len(grouped.sense_relations) == 1
    edge = grouped.sense_relations[0]
    by_text = {lem.text: lem.id for lem in grouped.lemmas}
    members = {by_text["hot"], by_text["cold"]}
    sense_ids = {s.id for s in grouped.senses if s.lemma_id in members}
    assert {edge.sense_id_a, edge.sense_id_b} == sense_ids
    assert edge.relation_type == "antonym"
    assert edge.sense_id_a < edge.sense_id_b


def test_sense_link_with_an_unresolved_end_is_dropped() -> None:
    entries = [
        SynsetEntry(
            "en",
            "en-1",
            "i1",
            "of high temperature",
            ("hot",),
            pos="a",
            sense_links=(
                SenseLink("hot", "antonym", "en-missing", "cold"),  # no such synset
                SenseLink("hot", "antonym", "en-2", "chilly"),  # not a member there
            ),
        ),
        SynsetEntry("en", "en-2", "i2", "of low temperature", ("cold",), pos="a"),
    ]
    grouped = group_to_records(entries)
    assert grouped.sense_relations == []
    assert grouped.relations == []


def test_domain_topics_gather_per_concept() -> None:
    entries = [
        SynsetEntry(
            "en",
            "en-1",
            "i1",
            "a football move",
            ("tackle",),
            pos="n",
            domain_topics=("football",),
        ),
        SynsetEntry("pt", "pt-1", "i1", None, ("placagem",), pos="n"),
        SynsetEntry("en", "en-2", "i2", "a tree", ("oak",), pos="n"),
    ]
    grouped = group_to_records(entries)
    assert grouped.concept_domains == {_cid(grouped, "a football move"): {"football"}}


def test_a_lemma_takes_its_majority_pos() -> None:
    # "go" is met first as a noun, then as a verb in two synsets.
    entries = [
        SynsetEntry("en", "n1", "i1", "a board game", ("go",), pos="n"),
        SynsetEntry("en", "v1", "i2", "change location", ("go",), pos="v"),
        SynsetEntry("en", "v2", "i3", "follow a procedure", ("go",), pos="v"),
    ]
    (lemma,) = group_to_records(entries).lemmas
    assert (lemma.text, lemma.part_of_speech) == ("go", "verb")


def test_a_pos_tie_goes_to_the_first_pos() -> None:
    entries = [
        SynsetEntry("en", "v1", "i2", "a made-up verb sense", ("run",), pos="v"),
        SynsetEntry("en", "n1", "i1", "a score in baseball", ("run",), pos="n"),
    ]
    (lemma,) = group_to_records(entries).lemmas
    assert lemma.part_of_speech == "noun"


def test_case_and_accent_variants_are_separate_lemmas() -> None:
    # Beryllium is not "be"; avó is not avô.
    entries = [
        SynsetEntry("en", "n1", "i1", "metallic element", ("Be", "beryllium"), pos="n"),
        SynsetEntry("en", "v1", "i2", "have the quality of being", ("be",), pos="v"),
        SynsetEntry("pt", "pn1", "i3", "", ("avó",), pos="n"),
        SynsetEntry("pt", "pn2", "i4", "", ("avô",), pos="n"),
    ]
    texts = sorted(lemma.text for lemma in group_to_records(entries).lemmas)
    assert texts == ["Be", "avó", "avô", "be", "beryllium"]


def test_capitalization_noise_folds_to_lowercase() -> None:
    entries = [
        # pt "Cuspir" beside "cuspir" in one synset: one word.
        SynsetEntry("en", "v1", "i1", "expel saliva", ("spit",), pos="v"),
        SynsetEntry("pt", "pv1", "i1", "", ("Cuspir", "cuspir"), pos="v"),
        # pt "Abstrato" alone, on a concept with no capitalized English member.
        SynsetEntry("en", "a1", "i2", "existing in the mind", ("abstract",), pos="a"),
        SynsetEntry("pt", "pa1", "i2", "", ("Abstrato",), pos="a"),
        # pt "ONU": its concept's English member "UN" is capitalized, so it stays.
        SynsetEntry("en", "n1", "i3", "a league of nations", ("UN",), pos="n"),
        SynsetEntry("pt", "pn1", "i3", "", ("ONU",), pos="n"),
        # en "State" vs "state" on different concepts: two words, never folded.
        SynsetEntry("en", "n2", "i4", "a territory", ("State",), pos="n"),
        SynsetEntry("en", "n3", "i5", "the way something is", ("state",), pos="n"),
    ]
    lemmas = group_to_records(entries).lemmas
    pt = sorted(lemma.text for lemma in lemmas if lemma.language == "pt")
    assert pt == ["ONU", "abstrato", "cuspir"]  # Cuspir and Abstrato folded
    en = sorted(lemma.text for lemma in lemmas if lemma.language == "en")
    assert en == ["State", "UN", "abstract", "spit", "state"]


def test_variant_spellings_of_one_meaning_fold_together() -> None:
    entries = [
        # Lost accent on one meaning: the fuller spelling wins.
        SynsetEntry("en", "n1", "i1", "becoming aware", ("perception",), pos="n"),
        SynsetEntry("es", "en1", "i1", "", ("percepcion", "percepción"), pos="n"),
        # Two norms with as many marks each stay apart.
        SynsetEntry("en", "n2", "i2", "irreverence", ("blasphemy",), pos="n"),
        SynsetEntry("pt", "pn2", "i2", "", ("blasfémia", "blasfêmia"), pos="n"),
        # Case variants of one name: the most capitalized wins.
        SynsetEntry("en", "n3", "i3", "a bridge", ("Golden Gate Bridge",), pos="n"),
        SynsetEntry(
            "pt", "pn3", "i3", "", ("Golden gate bridge", "Golden Gate Bridge"), pos="n"
        ),
        # Accent variants on different meanings are different words.
        SynsetEntry("en", "n4", "i4", "a monkey", ("monkey",), pos="n"),
        SynsetEntry("es", "en4", "i4", "", ("mono",), pos="n"),
        SynsetEntry("en", "n5", "i5", "a hair bun", ("bun",), pos="n"),
        SynsetEntry("es", "en5", "i5", "", ("moño",), pos="n"),
    ]
    texts = {(lemma.language, lemma.text) for lemma in group_to_records(entries).lemmas}
    assert ("es", "percepcion") not in texts
    assert ("es", "percepción") in texts
    assert {("pt", "blasfémia"), ("pt", "blasfêmia")} <= texts
    assert ("pt", "Golden Gate Bridge") in texts
    assert ("pt", "Golden gate bridge") not in texts
    assert {("es", "mono"), ("es", "moño")} <= texts


def test_joined_variants_split_into_separate_forms() -> None:
    assert member_forms("maire ; bourgmestre") == (["maire", "bourgmestre"], 0)
    assert member_forms("GAP!") == ([], 1)
    assert member_forms("bail|bau|baux", "fr") == (["bail", "bau", "baux"], 0)
    assert member_forms("déchoir|déchoir", "fr") == (["déchoir"], 0)
    # Tagged segments are translations: keep only the wordnet's own language.
    assert member_forms("bégonia|it=begonia|nl=begonia", "fr") == (["bégonia"], 0)
    assert member_forms("carnivora|fr:carnivore", "fr") == (
        ["carnivora", "carnivore"],
        0,
    )
    entries = [
        SynsetEntry("fr", "f1", "i1", None, ("maire ; bourgmestre",), pos="n"),
    ]
    assert {lem.text for lem in group_to_records(entries).lemmas} == {
        "maire",
        "bourgmestre",
    }


def test_member_counts_attach_to_the_right_sense() -> None:
    # SemCor counts ride along with the member forms, so they are attributed
    # while the ILI group is open - the corpus never persists the ILI, so this
    # is the only point the join can happen.
    entries = [
        SynsetEntry(
            "en",
            "s1",
            "i1",
            "a financial institution",
            ("bank", "depository"),
            member_counts=(30, 2),
            pos="n",
        ),
    ]
    grouped = group_to_records(entries)
    cid = grouped.concepts[0].id
    by_text = {lem.text: lem.id for lem in grouped.lemmas}
    assert grouped.sense_counts[by_text["bank"], cid] == 30
    assert grouped.sense_counts[by_text["depository"], cid] == 2
    assert grouped.concept_counts[cid] == 32


def test_untagged_english_concept_counts_zero_and_non_english_is_absent() -> None:
    entries = [
        SynsetEntry("en", "s1", "i1", "an untagged concept", ("alpha",), pos="n"),
        SynsetEntry("pt", "s2", "i2", "sem membro ingles", ("beta",), pos="n"),
    ]
    grouped = group_to_records(entries)

    def _concept_with(gloss: str) -> str:
        return next(c.id for c in grouped.concepts if gloss in c.definitions.values())

    english = _concept_with("an untagged concept")
    portuguese = _concept_with("sem membro ingles")
    assert grouped.concept_counts[english] == 0
    assert portuguese not in grouped.concept_counts


def test_counts_follow_a_form_that_merges_into_an_existing_lemma() -> None:
    # Two synsets naming the same form: one lemma, two senses, counts kept apart.
    entries = [
        SynsetEntry(
            "en",
            "s1",
            "i1",
            "a financial institution",
            ("bank",),
            member_counts=(30,),
            pos="n",
        ),
        SynsetEntry(
            "en",
            "s2",
            "i2",
            "sloping land",
            ("bank",),
            member_counts=(10,),
            pos="n",
        ),
    ]
    grouped = group_to_records(entries)
    assert len(grouped.lemmas) == 1
    assert sorted(grouped.sense_counts.values()) == [10, 30]


def test_counts_of_a_dropped_malformed_form_are_dropped_with_it() -> None:
    entries = [
        SynsetEntry(
            "en",
            "s1",
            "i1",
            "with a placeholder",
            ("real", "GAP!"),
            member_counts=(7, 5),
            pos="n",
        ),
    ]
    grouped = group_to_records(entries)
    cid = grouped.concepts[0].id
    assert [lem.text for lem in grouped.lemmas] == ["real"]
    # The placeholder's count goes with it; only the real form's is kept.
    assert list(grouped.sense_counts.values()) == [7]
    assert grouped.concept_counts[cid] == 7


def test_misaligned_member_counts_are_rejected_not_truncated() -> None:
    # Zip-truncating would silently move counts onto the wrong words.
    entry = SynsetEntry(
        "en",
        "s1",
        "i1",
        "two members, one count",
        ("alpha", "beta"),
        member_counts=(3,),
        pos="n",
    )
    with pytest.raises(MemberCountMismatchError):
        group_to_records([entry])
