"""TutorResponseChain: produce a correction + conversation continuation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_core.chains.structured_chain import StructuredLLMChain
from llm_core.data_models.basemodel_kwargs import BaseModelKwargs
from pydantic import BaseModel
from pydantic import Field

from lang_tools.llm._common import load_prompt

if TYPE_CHECKING:
    from pathlib import Path

    from llm_core.chat.config.base import ChatConfig

    from lang_tools.exercises.conversational_tutor import TutorMessage


class ErrorDetail(BaseModel):
    """Structured grammar / vocabulary error.

    Attributes:
        original: The user's wording.
        corrected: The corrected wording.
        explanation: Brief grammar / vocab note.
    """

    original: str
    corrected: str
    explanation: str


class CorrectionBlock(BaseModel):
    """Tutor's correction block.

    Attributes:
        content: Correction text in the target language.
        translation: Translation of the correction text.
        errors: Structured list of individual errors.
    """

    content: str = ""
    translation: str = ""
    errors: list[ErrorDetail] = Field(default_factory=list)


class ConversationBlock(BaseModel):
    """Tutor's conversation continuation.

    Attributes:
        content: Continuation text in the target language.
        translation: Translation of the continuation.
    """

    content: str
    translation: str


class TutorInput(BaseModelKwargs):
    """Inputs to `TutorResponseChain`.

    Attributes:
        topic: Conversation topic.
        language: ISO 639-1 target language code.
        user_message: Latest user message.
        history: Prior `TutorMessage`s.
        difficulty_level: ``"beginner"`` / ``"intermediate"`` / ``"advanced"``.
    """

    topic: str
    language: str
    user_message: str
    history: list[TutorMessage] = Field(default_factory=list)
    difficulty_level: str = "intermediate"


class TutorOutput(BaseModel):
    """Outputs from `TutorResponseChain`.

    Attributes:
        correction: Correction block (may be empty when no errors).
        conversation: Conversation continuation block.
    """

    correction: CorrectionBlock
    conversation: ConversationBlock


def build_tutor_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[TutorInput, TutorOutput]:
    """Build a tutor response chain wired to `chat_config`."""
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "tutor_response",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=TutorInput,
        output_model=TutorOutput,
    )
