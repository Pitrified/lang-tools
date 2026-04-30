"""Tests for `lang_tools.exercises.sentence_reconstruction`."""

import random

from lang_tools.exercises.sentence_reconstruction import SentenceReconstructionExercise
from lang_tools.exercises.sentence_reconstruction import merge_short_portions


def test_merge_short_portions_combines_with_neighbour() -> None:
    out = merge_short_portions(["hi", "there", "is", "world"])
    # "hi" too short -> merges into next; "is" too short -> merges into prev
    assert all(len(p) >= 3 for p in out)


def test_sentence_reconstruction_correct_submission() -> None:
    ex = SentenceReconstructionExercise(rng=random.Random(0))
    round_ = ex.start("Eu amo voce", "I love you", portions=["Eu", "amo", "voce"])
    expected = round_.expected
    result = ex.submit(round_, expected)
    assert result.correct is True


def test_sentence_reconstruction_wrong_submission() -> None:
    ex = SentenceReconstructionExercise(rng=random.Random(0))
    round_ = ex.start("Eu amo voce", "I love you", portions=["Eu", "amo", "voce"])
    bad = list(reversed(round_.expected))
    if bad == round_.expected:
        bad = [*bad[::-1], bad[0]]
    result = ex.submit(round_, bad)
    assert result.correct is False
