"""Tests for `lang_tools.lexicon.sense`."""

from lang_tools.lexicon.sense import Sense
from lang_tools.lexicon.sense_id import sense_id


def test_sense_id_is_computed_from_endpoints() -> None:
    sense = Sense(lemma_id="lem123", concept_id="c__bank-river__0011aabbccdd")
    assert sense.id == sense_id("lem123", "c__bank-river__0011aabbccdd")


def test_sense_id_stable_across_instances() -> None:
    a = Sense(lemma_id="lem123", concept_id="c__bank-river__0011aabbccdd")
    b = Sense(
        lemma_id="lem123",
        concept_id="c__bank-river__0011aabbccdd",
        token_frequency=0.5,
    )
    assert a.id == b.id


def test_sense_per_sense_fields_default_empty() -> None:
    sense = Sense(lemma_id="lem123", concept_id="c__bank-river__0011aabbccdd")
    assert sense.token_frequency is None
    assert sense.sense_frequency is None
    assert sense.cefr_level is None
    assert sense.frequency_is_estimated is False
    assert sense.cefr_is_estimated is False


def test_sense_round_trip() -> None:
    sense = Sense(
        lemma_id="lem123",
        concept_id="c__bank-river__0011aabbccdd",
        sense_frequency=0.3,
        cefr_level="B1",
    )
    dumped = sense.model_dump()
    assert Sense.model_validate(dumped) == sense
    # The computed id serializes but no representation back-refs leak in.
    assert "lemma" not in dumped
    assert "concept" not in dumped
