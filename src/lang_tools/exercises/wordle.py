"""Wordle exercise (from `worldly-words`).

Guess a hidden word within ``word_length + 1`` attempts. After each guess,
each letter receives a state: ``correct`` (right letter, right position),
``misplaced`` (right letter, wrong position), or ``wrong``. Comparison is done
on accent-stripped (`normalized`) forms.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from dataclasses import field
from typing import TYPE_CHECKING
from typing import Literal

from pydantic import BaseModel

from lang_tools.exercises.base import ExerciseRound
from lang_tools.exercises.base import RoundResult
from lang_tools.exercises.base import WordResult
from lang_tools.exercises.base import _BaseExercise
from lang_tools.language.normalization import normalize as _normalize

if TYPE_CHECKING:
    from lang_tools.words.word import Word

LetterState = Literal["correct", "misplaced", "wrong", "unused"]


class LetterResult(BaseModel):
    """Per-letter evaluation of a guess.

    Attributes:
        letter: The character (in the guess form, accent-stripped).
        state: One of ``"correct"``, ``"misplaced"``, ``"wrong"``.
    """

    letter: str
    state: LetterState


def _evaluate(guess: str, target: str) -> list[LetterResult]:
    results: list[LetterResult] = [
        LetterResult(letter=ch, state="wrong") for ch in guess
    ]
    remaining: Counter[str] = Counter()
    for i, ch in enumerate(target):
        if guess[i] == ch:
            results[i] = LetterResult(letter=ch, state="correct")
        else:
            remaining[ch] += 1
    for i, lr in enumerate(results):
        if lr.state == "correct":
            continue
        if remaining[lr.letter] > 0:
            results[i] = LetterResult(letter=lr.letter, state="misplaced")
            remaining[lr.letter] -= 1
    return results


@dataclass
class _WordleState:
    target: Word
    target_normalized: str
    word_length: int
    max_attempts: int
    guesses: list[str] = field(default_factory=list)
    results: list[list[LetterResult]] = field(default_factory=list)
    keyboard_state: dict[str, LetterState] = field(default_factory=dict)
    won: bool = False


def _update_keyboard(
    keyboard: dict[str, LetterState],
    letter_results: list[LetterResult],
) -> None:
    rank: dict[LetterState, int] = {
        "correct": 3,
        "misplaced": 2,
        "wrong": 1,
        "unused": 0,
    }
    for lr in letter_results:
        previous = keyboard.get(lr.letter, "unused")
        if rank[lr.state] > rank[previous]:
            keyboard[lr.letter] = lr.state


@dataclass
class WordleExercise(_BaseExercise):
    """Wordle round factory."""

    def __init__(self, **kwargs: object) -> None:
        """Initialize the exercise.

        Args:
            **kwargs: Forwarded to `_BaseExercise`.
        """
        super().__init__(exercise_type="wordle", **kwargs)  # type: ignore[arg-type]

    def start(self, target: Word, *, max_attempts: int | None = None) -> ExerciseRound:
        """Build a Wordle round around `target`.

        Args:
            target: The hidden word.
            max_attempts: Override for the default ``len(target) + 1``.

        Returns:
            `ExerciseRound` whose `expected` is the internal `_WordleState`.
        """
        self._ensure_started()
        normalized = _normalize(target.text)
        state = _WordleState(
            target=target,
            target_normalized=normalized,
            word_length=len(normalized),
            max_attempts=(
                max_attempts if max_attempts is not None else len(normalized) + 1
            ),
        )
        return ExerciseRound(
            prompt={
                "word_length": state.word_length,
                "max_attempts": state.max_attempts,
                "guesses": [],
                "results": [],
                "keyboard_state": {},
            },
            expected=state,
        )

    def submit(self, round_: ExerciseRound, guess: str) -> RoundResult:
        """Evaluate a single guess.

        Args:
            round_: The round returned by `start`.
            guess: User's guess. Compared against the normalized target.

        Returns:
            `RoundResult` flagging this guess. When the round terminates (win
            or attempts exhausted) a `WordResult` is appended.
        """
        state: _WordleState = round_.expected

        if state.won or len(state.guesses) >= state.max_attempts:
            return RoundResult(correct=False, feedback="Game already finished.")

        normalized_guess = _normalize(guess)
        if len(normalized_guess) != state.word_length:
            return RoundResult(
                correct=False,
                feedback=f"Guess must be {state.word_length} letters.",
            )

        letter_results = _evaluate(normalized_guess, state.target_normalized)
        state.guesses.append(normalized_guess)
        state.results.append(letter_results)
        _update_keyboard(state.keyboard_state, letter_results)

        round_.prompt["guesses"] = list(state.guesses)
        round_.prompt["results"] = [list(r) for r in state.results]
        round_.prompt["keyboard_state"] = dict(state.keyboard_state)

        correct = normalized_guess == state.target_normalized
        state.won = correct
        terminated = correct or len(state.guesses) >= state.max_attempts

        word_results: list[WordResult] = []
        if terminated:
            word_results.append(WordResult(word_id=state.target.id, correct=correct))

        result = RoundResult(
            correct=correct,
            feedback=None if correct else f"{guess!r} is not the word.",
            word_results=word_results,
        )
        self._bookkeep(result)
        return result
