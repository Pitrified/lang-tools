"""GreetingGeneratorChain: open a conversational tutor session."""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_core.chains.structured_chain import StructuredLLMChain
from llm_core.data_models.basemodel_kwargs import BaseModelKwargs
from pydantic import BaseModel

from lang_tools.llm._common import load_prompt

if TYPE_CHECKING:
    from pathlib import Path

    from llm_core.chat.config.base import ChatConfig


class GreetingInput(BaseModelKwargs):
    """Inputs to `GreetingGeneratorChain`.

    Attributes:
        topic: Topic the conversation will revolve around.
        language: ISO 639-1 target language code.
        difficulty_level: ``"beginner"`` / ``"intermediate"`` / ``"advanced"``.
    """

    topic: str
    language: str
    difficulty_level: str = "intermediate"


class GreetingOutput(BaseModel):
    """Outputs from `GreetingGeneratorChain`.

    Attributes:
        greeting: Greeting text in the target language.
        translation: Translation in the user's language.
    """

    greeting: str
    translation: str


def build_greeting_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[GreetingInput, GreetingOutput]:
    """Build a greeting generator chain wired to `chat_config`."""
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "greeting_generator",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=GreetingInput,
        output_model=GreetingOutput,
    )
