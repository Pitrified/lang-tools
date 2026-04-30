"""Tests for `lang_tools.exercises.wordle`."""

from lang_tools.exercises.wordle import WordleExercise
from lang_tools.exercises.wordle import _evaluate
from lang_tools.words.word import Word


def _word(text: str = "amor") -> Word:
    return Word(text=text, language="pt", part_of_speech="noun", frequency="medium")


def test_evaluate_marks_correct_misplaced_wrong() -> None:
    # target="amor", guess="omar": o misplaced, m correct, a misplaced, r correct
    res = _evaluate("omar", "amor")
    states = [r.state for r in res]
    assert states == ["misplaced", "correct", "misplaced", "correct"]


def test_wordle_correct_guess() -> None:
    ex = WordleExercise()
    round_ = ex.start(_word("amor"))
    result = ex.submit(round_, "amor")
    assert result.correct is True
    assert result.word_results
    assert result.word_results[0].correct is True


def test_wordle_wrong_length_rejected() -> None:
    ex = WordleExercise()
    round_ = ex.start(_word("amor"))
    result = ex.submit(round_, "am")
    assert result.correct is False


def test_wordle_exhausts_attempts() -> None:
    ex = WordleExercise()
    round_ = ex.start(_word("amor"), max_attempts=1)
    result = ex.submit(round_, "vida")
    assert result.correct is False
    assert result.word_results
    assert result.word_results[0].correct is False
