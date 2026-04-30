"""Per-user per-word progress tracking.

`UserWordProgress` is the single state object updated after every exercise
round. The selector module reads these records to produce weighted random
samples that prioritise unseen / error-heavy words.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel
from pydantic import Field


class ExerciseStats(BaseModel):
    """Per-exercise-type breakdown of progress.

    Attributes:
        seen_count: Times the user has been shown the word in this exercise.
        correct_count: Times the user answered correctly.
        error_count: Times the user answered incorrectly.
        last_seen_at: Most recent encounter timestamp.
    """

    seen_count: int = 0
    correct_count: int = 0
    error_count: int = 0
    last_seen_at: datetime | None = None

    def record(self, *, correct: bool, when: datetime | None = None) -> None:
        """Update counters with the result of one round.

        Args:
            correct: Whether the user answered correctly.
            when: Timestamp to use; defaults to ``datetime.now()``.
        """
        self.seen_count += 1
        if correct:
            self.correct_count += 1
        else:
            self.error_count += 1
        self.last_seen_at = when if when is not None else datetime.now()  # noqa: DTZ005


class UserWordProgress(BaseModel):
    """Per-user per-word performance record.

    Attributes:
        user_id: Opaque user identifier.
        word_id: ID of the associated `Word`.
        seen_count: Total times shown across all exercises.
        correct_count: Total correct answers across all exercises.
        error_count: Total incorrect answers across all exercises.
        last_seen_at: Most recent encounter across all exercises.
        is_useless: User-flagged irrelevant; selectors must skip these.
        exercise_stats: Per-exercise-type breakdown keyed by exercise type.
    """

    user_id: str
    word_id: str
    seen_count: int = 0
    correct_count: int = 0
    error_count: int = 0
    last_seen_at: datetime | None = None
    is_useless: bool = False
    exercise_stats: dict[str, ExerciseStats] = Field(default_factory=dict)

    def record(
        self,
        *,
        correct: bool,
        exercise_type: str | None = None,
        when: datetime | None = None,
    ) -> None:
        """Update aggregate counters and (optionally) per-exercise stats.

        Args:
            correct: Whether the user answered correctly.
            exercise_type: Optional exercise tag to also update.
            when: Timestamp to use; defaults to ``datetime.now()``.
        """
        when = when if when is not None else datetime.now()  # noqa: DTZ005
        self.seen_count += 1
        if correct:
            self.correct_count += 1
        else:
            self.error_count += 1
        self.last_seen_at = when

        if exercise_type is not None:
            stats = self.exercise_stats.setdefault(exercise_type, ExerciseStats())
            stats.record(correct=correct, when=when)
