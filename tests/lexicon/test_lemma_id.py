"""Tests for `lang_tools.lexicon.lemma_id`."""

from lang_tools.lexicon.lemma_id import lemma_id


def test_lemma_id_is_deterministic() -> None:
    assert lemma_id("café", "fr") == lemma_id("café", "fr")
    # Composed and decomposed spellings, and stray whitespace, are one id.
    assert lemma_id("cafe\u0301 ", "fr") == lemma_id("caf\u00e9", "fr")


def test_lemma_id_keeps_accents_and_case() -> None:
    assert lemma_id("avó", "pt") != lemma_id("avô", "pt")
    assert lemma_id("ordenar", "es") != lemma_id("ordeñar", "es")
    assert lemma_id("Be", "en") != lemma_id("be", "en")


def test_lemma_id_differs_per_language() -> None:
    assert lemma_id("amor", "pt") != lemma_id("amor", "es")
