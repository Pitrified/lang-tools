"""Tests for the phase-6 enrichment stage (`ingestion.enrich`).

Everything here runs on in-memory models: `enrich` is pure, and its only two
inputs (the Zipf mapping and the SemCor counts) are passed in, so none of this
needs ``wordfreq`` or ``wn``.
"""

from __future__ import annotations

import math

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.ingestion.enrich import CEFR_BANDS
from lang_tools.lexicon.ingestion.enrich import commonness_score
from lang_tools.lexicon.ingestion.enrich import difficulty_score
from lang_tools.lexicon.ingestion.enrich import enrich
from lang_tools.lexicon.ingestion.enrich import hypernym_depths
from lang_tools.lexicon.ingestion.enrich import linear_to_zipf
from lang_tools.lexicon.ingestion.enrich import score_to_band
from lang_tools.lexicon.ingestion.enrich import zipf_to_linear
from lang_tools.lexicon.ingestion.sources.omw import SynsetEntry
from lang_tools.lexicon.ingestion.transform import TaggedTables
from lang_tools.lexicon.ingestion.transform import transform
from lang_tools.lexicon.relations import RELATION_HYPERNYM
from lang_tools.lexicon.relations import ConceptRelation

_HOUSE = "c__house__000000000001"
_RIVER = "c__river__000000000002"
_BUILDING = "c__building__000000000003"


def _tables_two_senses() -> tuple[TaggedTables, str, str]:
    """One English lemma on two concepts, with SemCor counts 30 / 10."""
    entries = [
        SynsetEntry(
            "en", "en-1", "i001", "a financial institution", ("bank",),
            member_counts=(30,), pos="n",
        ),
        SynsetEntry(
            "en", "en-2", "i002", "sloping land beside water", ("bank",),
            member_counts=(10,), pos="n",
        ),
    ]
    tables = transform(entries)
    money, slope = (c.id for c in tables.concepts)
    return tables, money, slope


def test_zipf_round_trips_through_linear_space() -> None:
    assert math.isclose(linear_to_zipf(zipf_to_linear(4.2)), 4.2)
    # Zipf 3.0 is one occurrence per million words, by definition.
    assert math.isclose(zipf_to_linear(3.0), 1e-6)


def test_sense_frequency_splits_in_linear_space_not_log_space() -> None:
    tables, _, _ = _tables_two_senses()
    enrich(tables, zipf_by_form={("bank", "en"): 4.0})

    senses = sorted(tables.senses, key=lambda s: s.sense_frequency or 0.0, reverse=True)
    high, low = senses
    # Both keep the lemma's token frequency: it is a property of the form.
    assert high.token_frequency == 4.0
    assert low.token_frequency == 4.0
    assert high.sense_frequency is not None
    assert low.sense_frequency is not None
    # The split is a partition of the linear frequency, so the parts sum back to
    # the whole. Adding the zipf values instead would be meaningless.
    total = zipf_to_linear(high.sense_frequency) + zipf_to_linear(low.sense_frequency)
    assert math.isclose(total, zipf_to_linear(4.0))
    # Weights 30 and 10, Laplace smoothed: 31/42 and 11/42.
    assert math.isclose(zipf_to_linear(high.sense_frequency) / total, 31 / 42)


def test_smoothing_keeps_an_untagged_sense_above_zero() -> None:
    entries = [
        SynsetEntry(
            "en", "en-1", "i001", "a tagged meaning", ("word",),
            member_counts=(50,), pos="n",
        ),
        SynsetEntry("en", "en-2", "i002", "an untagged meaning", ("word",), pos="n"),
    ]
    tables = transform(entries)
    enrich(tables, zipf_by_form={("word", "en"): 3.0})

    frequencies = [s.sense_frequency for s in tables.senses]
    assert all(f is not None for f in frequencies)
    measured = [f for f in frequencies if f is not None]
    # Without smoothing the untagged sense would be exactly zero frequency,
    # i.e. minus infinity on the zipf scale.
    assert all(f > -math.inf for f in measured)
    assert min(measured) < max(measured)


def test_unknown_form_leaves_frequency_none_never_zero() -> None:
    tables, _, _ = _tables_two_senses()
    enrich(tables, zipf_by_form={})
    for sense in tables.senses:
        # A missing key means "no frequency", not "frequency zero" - wordfreq
        # returns 0.0 for both unknown and vanishingly rare, so we store neither.
        assert sense.token_frequency is None
        assert sense.sense_frequency is None


def test_english_tagged_single_word_sense_is_measured_not_estimated() -> None:
    tables, _, _ = _tables_two_senses()
    enrich(tables, zipf_by_form={("bank", "en"): 4.0})
    assert all(not s.frequency_is_estimated for s in tables.senses)


def test_non_english_sense_is_always_estimated() -> None:
    entries = [
        SynsetEntry(
            "en", "en-1", "i001", "a building", ("house",),
            member_counts=(12,), pos="n",
        ),
        SynsetEntry("pt", "pt-1", "i001", "uma moradia", ("casa",), pos="n"),
    ]
    tables = transform(entries)
    enrich(tables, zipf_by_form={("house", "en"): 4.0, ("casa", "pt"): 5.0})

    by_lemma = {s.lemma_id: s for s in tables.senses}
    lemma_lang = {lem.id: lem.language for lem in tables.lemmas}
    for lemma_id, sense in by_lemma.items():
        if lemma_lang[lemma_id] == "pt":
            # Portuguese borrows the English split: there is no pt sense-tagged
            # corpus, so the value is a prior, and it says so.
            assert sense.frequency_is_estimated
        else:
            assert not sense.frequency_is_estimated


def test_multiword_form_is_estimated_because_wordfreq_composes_it() -> None:
    entries = [
        SynsetEntry(
            "en", "en-1", "i001", "the top officer", ("chief executive officer",),
            member_counts=(5,), pos="n",
        ),
    ]
    tables = transform(entries)
    enrich(tables, zipf_by_form={("chief executive officer", "en"): 2.5})
    # Tagged, English, single sense - and still estimated, because wordfreq
    # composed the phrase's score from its components instead of measuring it.
    assert tables.senses[0].frequency_is_estimated


def test_commonness_is_set_from_semcor_and_distinguishes_zero_from_absent() -> None:
    entries = [
        SynsetEntry(
            "en", "en-1", "i001", "a tagged concept", ("alpha",),
            member_counts=(99,), pos="n",
        ),
        # English member, never tagged -> counted zero, not absent.
        SynsetEntry("en", "en-2", "i002", "an untagged concept", ("beta",), pos="n"),
        # No English member at all -> nothing to count.
        SynsetEntry("pt", "pt-1", "i003", "sem membro ingles", ("gama",), pos="n"),
    ]
    tables = transform(entries)
    enrich(tables, zipf_by_form={})

    by_definition = {
        next(iter(c.definitions.values())): c.commonness for c in tables.concepts
    }
    assert by_definition["a tagged concept"] == commonness_score(99)
    assert by_definition["an untagged concept"] == 0.0
    assert by_definition["sem membro ingles"] is None


def test_commonness_compresses_the_skewed_semcor_distribution() -> None:
    # Phase 5.54 measured median 2, max 10,742: without the log the head would
    # swamp every other concept in the difficulty score.
    assert commonness_score(0) == 0.0
    assert commonness_score(9) == 1.0
    assert commonness_score(10_742) < 5.0


def test_hypernym_depth_counts_from_the_root() -> None:
    concepts = [Concept(id=_HOUSE), Concept(id=_RIVER), Concept(id=_BUILDING)]
    relations = [
        ConceptRelation(
            concept_id_a=_HOUSE,
            concept_id_b=_BUILDING,
            relation_type=RELATION_HYPERNYM,
        ),
    ]
    depths = hypernym_depths(concepts, relations)
    assert depths[_BUILDING] == 0  # a root: nothing broader
    assert depths[_HOUSE] == 1
    assert depths[_RIVER] == 0  # isolated concepts are roots too


def test_hypernym_depth_ignores_other_relation_types() -> None:
    concepts = [Concept(id=_HOUSE), Concept(id=_BUILDING)]
    relations = [
        ConceptRelation(
            concept_id_a=_HOUSE,
            concept_id_b=_BUILDING,
            relation_type="related",
        ),
    ]
    assert hypernym_depths(concepts, relations) == {_HOUSE: 0, _BUILDING: 0}


def test_difficulty_rises_as_a_word_gets_rarer() -> None:
    common = difficulty_score(zipf=6.0, commonness=2.0, depth=2, length=5)
    rare = difficulty_score(zipf=2.0, commonness=2.0, depth=2, length=5)
    assert rare > common


def test_difficulty_rises_with_depth_and_falls_with_commonness() -> None:
    base = {"zipf": 4.0, "length": 6}
    assert difficulty_score(commonness=2.0, depth=15, **base) > difficulty_score(
        commonness=2.0, depth=1, **base,
    )
    assert difficulty_score(commonness=0.0, depth=5, **base) > difficulty_score(
        commonness=3.0, depth=5, **base,
    )


def test_missing_inputs_are_neutral_not_hardest() -> None:
    # A concept with no English member has no commonness. That must not read as
    # "maximally obscure" - the signal is absent, not negative.
    unknown = difficulty_score(zipf=4.0, commonness=None, depth=None, length=6)
    hardest = difficulty_score(zipf=4.0, commonness=0.0, depth=20, length=6)
    assert unknown < hardest


def test_bands_are_ordered_and_cover_the_score_range() -> None:
    assert score_to_band(0.0) == CEFR_BANDS[0]
    assert score_to_band(1.0) == CEFR_BANDS[-1]
    seen = [score_to_band(i / 100) for i in range(101)]
    # Monotone: a harder score never lands in an easier band.
    assert [CEFR_BANDS.index(b) for b in seen] == sorted(
        CEFR_BANDS.index(b) for b in seen
    )


def test_every_band_is_flagged_estimated_including_english() -> None:
    tables, _, _ = _tables_two_senses()
    enrich(tables, zipf_by_form={("bank", "en"): 4.0})
    for sense in tables.senses:
        assert sense.cefr_level in CEFR_BANDS
        # Kelly is validation-only and never shipped, so no band anywhere comes
        # from a graded list - not even in the language Kelly covers.
        assert sense.cefr_is_estimated


def test_enrich_reports_coverage_counts() -> None:
    tables, _, _ = _tables_two_senses()
    stats = enrich(tables, zipf_by_form={("bank", "en"): 4.0})
    assert stats["with_frequency"] == 2
    assert stats["estimated"] == 0
    assert stats["with_band"] == 2
    assert sum(stats[f"band_{band}"] for band in CEFR_BANDS) == 2
