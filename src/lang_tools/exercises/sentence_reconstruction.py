"""Sentence reconstruction exercise (from `convo_craft`).

The user is shown the translation of a target-language sentence and a shuffled
list of word portions; they must tap them in correct order. The expected order
mirrors the source sentence, optionally split via an LLM `ParagraphSplitter`
(see `lang_tools.llm.splitter`) followed by `merge_short_portions`.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import random

from lang_tools.exercises.base import ExerciseRound
from lang_tools.exercises.base import RoundResult
from lang_tools.exercises.base import _BaseExercise

_MIN_PORTION_LEN = 3


def merge_short_portions(
    portions: list[str],
    min_len: int = _MIN_PORTION_LEN,
) -> list[str]:
    """Merge any portion shorter than `min_len` with its neighbour.

    Mirrors `convo_craft`'s local `SentenceSplitter` post-processing. Short
    portions are appended to the previous one (or prepended to the next one if
    they appear at the start).

    Args:
        portions: Raw portion list, typically from an LLM splitter.
        min_len: Minimum acceptable portion length in characters.

    Returns:
        New list with short portions merged.
    """
    if not portions:
        return []
    out: list[str] = []
    for portion in portions:
        if not out:
            out.append(portion)
            continue
        if len(portion) < min_len or len(out[-1]) < min_len:
            out[-1] = f"{out[-1]} {portion}".strip()
        else:
            out.append(portion)
    return out


@dataclass
class SentenceReconstructionExercise(_BaseExercise):
    """Sentence reconstruction round factory.

    Attributes:
        rng: Optional `random.Random` for deterministic shuffles.
    """

    rng: random.Random = field(default_factory=random.SystemRandom)

    def __init__(self, rng: random.Random | None = None, **kwargs: object) -> None:
        """Initialize the exercise with a deterministic RNG by default.

        Args:
            rng: Optional `random.Random`; defaults to `random.SystemRandom`.
            **kwargs: Forwarded to `_BaseExercise` (e.g. `progress_callback`).
        """
        super().__init__(exercise_type="sentence_reconstruction", **kwargs)  # type: ignore[arg-type]
        self.rng = rng or random.SystemRandom()

    def start(
        self,
        sentence: str,
        translation: str,
        *,
        portions: list[str] | None = None,
    ) -> ExerciseRound:
        """Build a round from a target-language sentence.

        Args:
            sentence: Target-language sentence the user must reconstruct.
            translation: User-language translation shown as the prompt.
            portions: Pre-split portions; defaults to a whitespace split.

        Returns:
            `ExerciseRound` whose `prompt` is a dict with shuffled portions.
        """
        self._ensure_started()
        ordered = merge_short_portions(
            portions if portions is not None else sentence.split(),
        )
        shuffled = ordered.copy()
        self.rng.shuffle(shuffled)
        return ExerciseRound(
            prompt={"translation": translation, "portions": shuffled},
            expected=ordered,
        )

    def submit(self, round_: ExerciseRound, selected_order: list[str]) -> RoundResult:
        """Score a user-submitted ordering.

        Args:
            round_: The round returned by `start`.
            selected_order: User's chosen portion order.

        Returns:
            `RoundResult` whose `correct` flag is True iff orderings match.
        """
        correct = selected_order == round_.expected
        result = RoundResult(
            correct=correct,
            feedback=None if correct else "Order does not match the expected sentence.",
        )
        self._bookkeep(result)
        return result
