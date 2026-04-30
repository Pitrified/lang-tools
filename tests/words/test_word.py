"""Tests for `lang_tools.words.word`."""

from lang_tools.words.word import Word


def test_word_normalizes_on_creation() -> None:
    word = Word(text="Café", language="fr", part_of_speech="noun", frequency="medium")
    assert word.normalized == "cafe"


def test_word_id_stable_across_instances() -> None:
    a = Word(text="café", language="fr", part_of_speech="noun", frequency="medium")
    b = Word(text="CAFÉ", language="fr", part_of_speech="noun", frequency="medium")
    assert a.id == b.id


def test_word_computed_properties() -> None:
    w = Word(text="café", language="fr", part_of_speech="noun", frequency="medium")
    assert w.length == 4
    assert w.has_accent is True
    assert "é" in w.accented_chars
