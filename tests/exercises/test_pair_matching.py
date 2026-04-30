"""Tests for `lang_tools.exercises.pair_matching`."""

import random

import pytest

from lang_tools.exercises.pair_matching import MissingTranslationError
from lang_tools.exercises.pair_matching import PairMatchingExercise
from lang_tools.words.word import Word


def _word(text: str, translations: dict[str, str]) -> Word:
    return Word(
        text=text,
        language="pt",
        part_of_speech="noun",
        frequency="medium",
        translations=translations,
    )


def test_pair_matching_correct_pair() -> None:
    words = [_word("amor", {"en": "love"}), _word("paz", {"en": "peace"})]
    ex = PairMatchingExercise(target_language="en", rng=random.Random(0))
    round_ = ex.start(words)
    result = ex.submit(round_, ("amor", "love"))
    assert result.correct is True


def test_pair_matching_wrong_pair() -> None:
    words = [_word("amor", {"en": "love"}), _word("paz", {"en": "peace"})]
    ex = PairMatchingExercise(target_language="en", rng=random.Random(0))
    round_ = ex.start(words)
    result = ex.submit(round_, ("amor", "peace"))
    assert result.correct is False


def test_missing_translation_raises() -> None:
    ex = PairMatchingExercise(target_language="en", rng=random.Random(0))
    with pytest.raises(MissingTranslationError):
        ex.start([_word("amor", {"fr": "amour"})])
