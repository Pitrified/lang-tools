"""ConversationGeneratorChain: generate a multi-turn bilingual dialogue."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal

from llm_core.chains.structured_chain import StructuredLLMChain
from llm_core.data_models.basemodel_kwargs import BaseModelKwargs
from pydantic import BaseModel
from pydantic import Field

from lang_tools.llm._common import load_prompt

if TYPE_CHECKING:
    from pathlib import Path

    from llm_core.chat.config.base import ChatConfig


class ConversationTurn(BaseModel):
    """One turn in a generated conversation.

    Attributes:
        role: ``"user"`` or ``"system"``.
        content: Target-language text.
        translation: User-language translation.
    """

    role: Literal["user", "system"]
    content: str
    translation: str


class ConversationInput(BaseModelKwargs):
    """Inputs to `ConversationGeneratorChain`.

    Attributes:
        topic: Topic prompt for the dialogue.
        language: ISO 639-1 code of the target language.
        difficulty_level: ``"beginner"`` / ``"intermediate"`` / ``"advanced"``.
        num_turns: How many turns the dialogue should contain.
        max_sentences_per_turn: Per-turn sentence cap.
        sample_conversation: Optional few-shot example to calibrate level.
    """

    topic: str
    language: str
    difficulty_level: str = "intermediate"
    num_turns: int = 6
    max_sentences_per_turn: int = 3
    sample_conversation: str | None = None


class ConversationOutput(BaseModel):
    """Outputs from `ConversationGeneratorChain`.

    Attributes:
        turns: Generated dialogue turns.
    """

    turns: list[ConversationTurn] = Field(default_factory=list)


def build_conversation_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[ConversationInput, ConversationOutput]:
    """Build a conversation generator chain wired to `chat_config`."""
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "conversation_generator",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=ConversationInput,
        output_model=ConversationOutput,
    )
