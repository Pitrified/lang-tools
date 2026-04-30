"""Conversational tutor exercise (from `fala-comigo-ai-tutor`).

This exercise is loosely coupled to `UserWordProgress`: each user turn is sent
to a `TutorResponseChain` (defined in `lang_tools.llm.tutor`) that produces a
correction block plus a conversation continuation. The chain itself is
provided by the caller so this module stays free of an LLM dependency.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel

from lang_tools.exercises.base import ExerciseRound
from lang_tools.exercises.base import RoundResult
from lang_tools.exercises.base import _BaseExercise


class TutorMessage(BaseModel):
    """One message in the tutor conversation history.

    Attributes:
        role: ``"user"`` or ``"tutor"``.
        content: Target-language text.
        translation: Optional user-language translation.
        correction: Optional correction block (tutor messages only).
    """

    role: Literal["user", "tutor"]
    content: str
    translation: str | None = None
    correction: str | None = None


TutorChain = Callable[[str, list[TutorMessage]], TutorMessage]
"""Callable that takes ``(user_text, history)`` and returns the tutor reply."""


@dataclass
class ConversationalTutorExercise(_BaseExercise):
    """Conversational tutor session driven by a caller-supplied chain.

    Attributes:
        chain: Callable matching the `TutorChain` signature.
        topic: Conversation topic shown to the user.
        history: Live conversation history; mutated in place.
    """

    chain: TutorChain | None = None
    topic: str = ""

    def __init__(
        self,
        chain: TutorChain | None = None,
        topic: str = "",
        **kwargs: object,
    ) -> None:
        """Initialize with an optional chain and topic.

        Args:
            chain: Callable matching `TutorChain`. May be ``None`` if the
                exercise will be driven manually.
            topic: Conversation topic.
            **kwargs: Forwarded to `_BaseExercise`.
        """
        super().__init__(exercise_type="conversational_tutor", **kwargs)  # type: ignore[arg-type]
        self.chain = chain
        self.topic = topic
        self.history: list[TutorMessage] = []

    def start(self, greeting: TutorMessage | None = None) -> ExerciseRound:
        """Open the session with an optional tutor greeting.

        Args:
            greeting: Initial tutor message; appended to history if provided.

        Returns:
            `ExerciseRound` whose `prompt` is the live `history` reference.
        """
        self._ensure_started()
        if greeting is not None:
            self.history.append(greeting)
        return ExerciseRound(
            prompt={"topic": self.topic, "history": self.history},
            expected=None,
        )

    def submit(self, round_: ExerciseRound, user_text: str) -> RoundResult:
        """Send a user message and append the tutor reply.

        Args:
            round_: The round returned by `start`.
            user_text: The user's target-language message.

        Returns:
            `RoundResult` whose `feedback` carries the correction block (if any)
            and `correct` is True when no correction was returned.

        Raises:
            RuntimeError: If `chain` is None when the user submits a message.
        """
        del round_  # state lives on the exercise
        if self.chain is None:
            msg = "ConversationalTutorExercise.chain must be set before submit()."
            raise RuntimeError(msg)

        self.history.append(TutorMessage(role="user", content=user_text))
        reply = self.chain(user_text, list(self.history))
        self.history.append(reply)

        correct = not (reply.correction and reply.correction.strip())
        result = RoundResult(
            correct=correct,
            feedback=reply.correction,
        )
        self._bookkeep(result)
        return result
