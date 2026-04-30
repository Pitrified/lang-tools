"""Common exercise interface shared by every mechanic.

Pattern rules:
    Each concrete exercise builds an `ExerciseRound`, evaluates user input via
    `submit`, and returns a `RoundResult` whose `word_results` feed back into
    `UserWordProgress`. Calling `finish()` aggregates a `SessionSummary` and
    optionally persists progress through a caller-supplied callback.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel
from pydantic import Field

ExerciseType = Literal[
    "sentence_reconstruction",
    "pair_matching",
    "conversational_tutor",
    "diacritic_typing",
    "wordle",
]

EXERCISE_TYPES: tuple[ExerciseType, ...] = (
    "sentence_reconstruction",
    "pair_matching",
    "conversational_tutor",
    "diacritic_typing",
    "wordle",
)


class WordResult(BaseModel):
    """Per-word outcome of a single round.

    Attributes:
        word_id: ID of the involved `Word`.
        correct: Whether the user got it right.
    """

    word_id: str
    correct: bool


class ExerciseRound(BaseModel):
    """Generic round container.

    Attributes:
        prompt: Exercise-specific prompt payload.
        expected: Exercise-specific expected answer used by `submit`.
    """

    prompt: Any
    expected: Any

    model_config = {"arbitrary_types_allowed": True}


class RoundResult(BaseModel):
    """Outcome of one `submit()` call.

    Attributes:
        correct: Whether the round overall counts as correct.
        feedback: Optional human-readable feedback message.
        word_results: Per-word outcomes for progress tracking.
    """

    correct: bool
    feedback: str | None = None
    word_results: list[WordResult] = Field(default_factory=list)


class SessionSummary(BaseModel):
    """Aggregate stats produced by `finish()`.

    Attributes:
        exercise_type: Tag of the originating exercise.
        total_rounds: Number of rounds played.
        correct_rounds: Number of rounds the user completed correctly.
        words_practiced: Distinct word IDs touched during the session.
        duration_seconds: Wall-clock duration in seconds.
    """

    exercise_type: ExerciseType
    total_rounds: int
    correct_rounds: int
    words_practiced: list[str]
    duration_seconds: float


ProgressCallback = Callable[[list[WordResult]], None]


@dataclass
class _BaseExercise:
    """Internal base providing session bookkeeping.

    Concrete exercises override `start` and `submit`.
    """

    exercise_type: ExerciseType
    progress_callback: ProgressCallback | None = None
    _started_at: datetime | None = field(default=None, init=False, repr=False)
    _total_rounds: int = field(default=0, init=False, repr=False)
    _correct_rounds: int = field(default=0, init=False, repr=False)
    _words_practiced: set[str] = field(default_factory=set, init=False, repr=False)

    def _bookkeep(self, result: RoundResult) -> None:
        self._total_rounds += 1
        if result.correct:
            self._correct_rounds += 1
        for wr in result.word_results:
            self._words_practiced.add(wr.word_id)
        if self.progress_callback is not None and result.word_results:
            self.progress_callback(result.word_results)

    def finish(self) -> SessionSummary:
        """Return aggregated stats for the session.

        Returns:
            `SessionSummary` with totals derived from every prior `submit`.
        """
        end = datetime.now()  # noqa: DTZ005
        start = self._started_at or end
        return SessionSummary(
            exercise_type=self.exercise_type,
            total_rounds=self._total_rounds,
            correct_rounds=self._correct_rounds,
            words_practiced=sorted(self._words_practiced),
            duration_seconds=(end - start).total_seconds(),
        )

    def _ensure_started(self) -> None:
        if self._started_at is None:
            self._started_at = datetime.now()  # noqa: DTZ005
