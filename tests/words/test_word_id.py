"""Tests for `lang_tools.words.word_id`."""

from lang_tools.words.word_id import word_id


def test_word_id_is_deterministic() -> None:
    assert word_id("Café", "fr") == word_id("café", "fr")


def test_word_id_differs_per_language() -> None:
    assert word_id("amor", "pt") != word_id("amor", "es")
