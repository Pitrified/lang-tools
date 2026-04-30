"""Tests for `lang_tools.exercises.diacritic_typing`."""

from lang_tools.exercises.diacritic_typing import DiacriticTypingExercise
from lang_tools.words.word import Word


def _word() -> Word:
    return Word(text="café", language="fr", part_of_speech="noun", frequency="medium")


def test_diacritic_typing_correct_keystroke() -> None:
    ex = DiacriticTypingExercise()
    round_ = ex.start(_word())
    result = ex.submit(round_, "c")
    assert result.correct is True


def test_diacritic_typing_wrong_keystroke_disables() -> None:
    ex = DiacriticTypingExercise()
    round_ = ex.start(_word())
    result = ex.submit(round_, "z")
    assert result.correct is False
    assert "z" in round_.prompt["disabled_keys"]


def test_diacritic_typing_completion_emits_word_result() -> None:
    ex = DiacriticTypingExercise()
    round_ = ex.start(_word())
    results = [ex.submit(round_, ch) for ch in "café"]
    final = results[-1]
    assert final.word_results
    assert final.word_results[0].correct is True
