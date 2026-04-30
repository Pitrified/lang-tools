"""Tests for `lang_tools.progress.progress`."""

from datetime import datetime

from lang_tools.progress.progress import ExerciseStats
from lang_tools.progress.progress import UserWordProgress


def test_record_increments_counters() -> None:
    p = UserWordProgress(user_id="u", word_id="w")
    p.record(correct=True, exercise_type="wordle")
    p.record(correct=False, exercise_type="wordle")
    stats: ExerciseStats = p.exercise_stats["wordle"]
    assert stats.seen_count == 2
    assert stats.correct_count == 1
    assert stats.error_count == 1
    assert isinstance(stats.last_seen_at, datetime)


def test_record_without_exercise_type_only_updates_word() -> None:
    p = UserWordProgress(user_id="u", word_id="w")
    p.record(correct=True)
    assert p.seen_count == 1
    assert p.exercise_stats == {}
