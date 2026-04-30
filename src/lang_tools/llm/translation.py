"""TranslationChain: translate text between any two supported languages."""

from __future__ import annotations

from typing import TYPE_CHECKING

from llm_core.chains.structured_chain import StructuredLLMChain
from llm_core.data_models.basemodel_kwargs import BaseModelKwargs
from pydantic import BaseModel

from lang_tools.llm._common import load_prompt

if TYPE_CHECKING:
    from pathlib import Path

    from llm_core.chat.config.base import ChatConfig


class TranslationInput(BaseModelKwargs):
    """Inputs to `TranslationChain`.

    Attributes:
        text: Source text.
        source_language: ISO 639-1 code of the source.
        target_language: ISO 639-1 code of the destination.
    """

    text: str
    source_language: str
    target_language: str


class TranslationOutput(BaseModel):
    """Outputs from `TranslationChain`.

    Attributes:
        translated_text: The translated string.
    """

    translated_text: str


def build_translation_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[TranslationInput, TranslationOutput]:
    """Build a translation chain wired to `chat_config`.

    Args:
        chat_config: `llm-core` `ChatConfig` (e.g. `ChatOpenAIConfig`).
        base_prompt_fol: Override prompts root; defaults to in-package folder.
        version: Prompt version (``"1"`` or ``"auto"``).

    Returns:
        `StructuredLLMChain` ready to `invoke` / `ainvoke`.
    """
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "translation",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=TranslationInput,
        output_model=TranslationOutput,
    )
