"""Tests for `lang_tools.lexicon.lemma`."""

from lang_tools.lexicon.lemma import Lemma


def test_lemma_normalizes_on_creation() -> None:
    lemma = Lemma(text="Café", language="fr", part_of_speech="noun")
    assert lemma.normalized == "cafe"


def test_lemma_id_stable_across_instances() -> None:
    a = Lemma(text="café", language="fr", part_of_speech="noun")
    b = Lemma(text="CAFÉ", language="fr", part_of_speech="noun")
    assert a.id == b.id


def test_lemma_computed_properties() -> None:
    lemma = Lemma(text="café", language="fr", part_of_speech="noun")
    assert lemma.length == 4
    assert lemma.has_accent is True
    assert "é" in lemma.accented_chars
