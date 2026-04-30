"""Pair matching exercise (from `brazilian-bites`).

Given N words, the user matches each one to its translation drawn from a
shuffled column. Each `submit` call evaluates a single ``(left, right)`` tap.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import random
from typing import TYPE_CHECKING

from lang_tools.exercises.base import ExerciseRound
from lang_tools.exercises.base import RoundResult
from lang_tools.exercises.base import WordResult
from lang_tools.exercises.base import _BaseExercise

if TYPE_CHECKING:
    from lang_tools.words.word import Word


class MissingTranslationError(KeyError):
    """Raised when a word does not carry a translation in the target language."""

    def __init__(self, word: Word, target_language: str) -> None:
        """Initialize with the offending word and the missing target language.

        Args:
            word: The `Word` that lacks a translation.
            target_language: Target ISO 639-1 code that was requested.
        """
        super().__init__(
            f"Word {word.text!r} has no translation in {target_language!r}",
        )
        self.word = word
        self.target_language = target_language


@dataclass
class PairMatchingExercise(_BaseExercise):
    """Pair-matching round factory.

    Attributes:
        target_language: ISO 639-1 code for the translations side.
        rng: Optional `random.Random` for deterministic shuffles.
    """

    target_language: str = "en"
    rng: random.Random = field(default_factory=random.SystemRandom)

    def __init__(
        self,
        target_language: str = "en",
        rng: random.Random | None = None,
        **kwargs: object,
    ) -> None:
        """Initialize with the translation language and an optional RNG.

        Args:
            target_language: ISO 639-1 code used to look up `Word.translations`.
            rng: Optional `random.Random`; defaults to `random.SystemRandom`.
            **kwargs: Forwarded to `_BaseExercise`.
        """
        super().__init__(exercise_type="pair_matching", **kwargs)  # type: ignore[arg-type]
        self.target_language = target_language
        self.rng = rng or random.SystemRandom()

    def start(self, words: list[Word]) -> ExerciseRound:
        """Build a round from a list of words.

        Args:
            words: The words to match. Each must have a translation in
                `target_language`.

        Returns:
            `ExerciseRound` whose `prompt` carries the left/right columns and
            `expected` the correct mapping ``{left_text: right_text}``.

        Raises:
            MissingTranslationError: When any word lacks a translation in
                `target_language`.
        """
        self._ensure_started()
        pairs: dict[str, str] = {}
        word_by_text: dict[str, Word] = {}
        for word in words:
            translation = word.translations.get(self.target_language)
            if translation is None:
                raise MissingTranslationError(word, self.target_language)
            pairs[word.text] = translation
            word_by_text[word.text] = word

        right_column = list(pairs.values())
        self.rng.shuffle(right_column)
        return ExerciseRound(
            prompt={
                "left_words": list(pairs.keys()),
                "right_words": right_column,
            },
            expected={"pairs": pairs, "word_by_text": word_by_text},
        )

    def submit(
        self,
        round_: ExerciseRound,
        selected_pair: tuple[str, str],
    ) -> RoundResult:
        """Score a single ``(left_word, right_word)`` tap.

        Args:
            round_: The round returned by `start`.
            selected_pair: The user's chosen ``(left, right)`` pair.

        Returns:
            `RoundResult` reflecting whether the right value matches the
            expected translation for the left word. Includes one `WordResult`
            for the left word.
        """
        left, right = selected_pair
        expected_pairs: dict[str, str] = round_.expected["pairs"]
        word_by_text: dict[str, Word] = round_.expected["word_by_text"]
        correct = expected_pairs.get(left) == right
        word_results: list[WordResult] = []
        if left in word_by_text:
            word_results.append(
                WordResult(word_id=word_by_text[left].id, correct=correct),
            )
        result = RoundResult(
            correct=correct,
            feedback=None if correct else "Wrong pair.",
            word_results=word_results,
        )
        self._bookkeep(result)
        return result
