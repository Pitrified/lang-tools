"""Tests for `lang_tools.lexicon.lemma_id`."""

from lang_tools.lexicon.lemma_id import lemma_id


def test_lemma_id_is_deterministic() -> None:
    assert lemma_id("Café", "fr") == lemma_id("café", "fr")


def test_lemma_id_differs_per_language() -> None:
    assert lemma_id("amor", "pt") != lemma_id("amor", "es")
