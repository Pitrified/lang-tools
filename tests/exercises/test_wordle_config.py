"""Tests for `lang_tools.exercises.wordle_config`."""

from lang_tools.exercises.wordle_config import WordleConfig


def test_default_word_lengths() -> None:
    config = WordleConfig()
    assert config.word_lengths == [4, 5, 6, 7]


def test_default_word_length() -> None:
    config = WordleConfig()
    assert config.default_word_length == 5


def test_custom_values_round_trip() -> None:
    config = WordleConfig(word_lengths=[5, 6], default_word_length=6)
    assert config.word_lengths == [5, 6]
    assert config.default_word_length == 6


def test_to_kw_returns_flat_dict() -> None:
    config = WordleConfig()
    kw = config.to_kw(exclude_none=True)
    assert kw["word_lengths"] == [4, 5, 6, 7]
    assert kw["default_word_length"] == 5


def test_importable_from_exercises_namespace() -> None:
    from lang_tools.exercises import WordleConfig as WordleConfigAlias  # noqa: PLC0415

    assert WordleConfigAlias is WordleConfig
