"""Tests for `lang_tools.progress.selection`."""

import random

from lang_tools.progress.progress import UserWordProgress
from lang_tools.progress.selection import SelectionWeights
from lang_tools.progress.selection import WordFilter
from lang_tools.progress.selection import compute_weight
from lang_tools.progress.selection import select_words
from lang_tools.words.word import Word


def _word(text: str = "amor", **extra: object) -> Word:
    return Word(
        text=text,
        language="pt",
        part_of_speech="noun",
        frequency="medium",
        **extra,  # type: ignore[arg-type]
    )


def test_useless_words_get_zero_weight() -> None:
    w = _word()
    progress = UserWordProgress(user_id="u", word_id=w.id, is_useless=True)
    assert compute_weight(w, progress, SelectionWeights()) == 0.0


def test_unseen_words_have_higher_weight_than_seen() -> None:
    seen_word = _word("paz")
    unseen_word = _word("amor")
    seen_progress = UserWordProgress(user_id="u", word_id=seen_word.id, seen_count=10)
    unseen_progress = UserWordProgress(user_id="u", word_id=unseen_word.id)
    weights = SelectionWeights()
    assert compute_weight(unseen_word, unseen_progress, weights) > compute_weight(
        seen_word, seen_progress, weights,
    )


def test_word_filter_min_length() -> None:
    short = _word("oi")
    long_word = _word("paciencia")
    f = WordFilter(min_length=4)
    assert not f.matches(short)
    assert f.matches(long_word)


def test_select_words_returns_distinct() -> None:
    pool = [_word(t) for t in ("amor", "paz", "luz", "vida", "sol")]
    progress: dict[str, UserWordProgress] = {}
    rng = random.Random(0)
    chosen = select_words(pool, progress, n=3, rng=rng)
    assert len(chosen) == 3
    assert len({w.id for w in chosen}) == 3
