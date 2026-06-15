"""LemmaGeneratorChain: generate themed vocabulary on demand."""

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


class GeneratedLemma(BaseModel):
    """One LLM-generated vocabulary item.

    Attributes:
        text: The lemma in the target language.
        translation: English translation.
        part_of_speech: Lemma class label.
        example_sentence: Example sentence in the target language.
        example_translation: English translation of the example sentence.
    """

    text: str
    translation: str
    part_of_speech: str
    example_sentence: str
    example_translation: str


class LemmaGeneratorInput(BaseModelKwargs):
    """Inputs to `LemmaGeneratorChain`.

    Attributes:
        language: ISO 639-1 target language code.
        topic: Theme to draw vocabulary from.
        num_lemmas: How many lemmas to produce.
        difficulty: ``"beginner"`` / ``"intermediate"`` / ``"advanced"``.
        require_accents: If True, only return lemmas containing accented chars.
    """

    language: str
    topic: str
    num_lemmas: int = 10
    difficulty: str = "intermediate"
    require_accents: bool = False


class LemmaGeneratorOutput(BaseModel):
    """Outputs from `LemmaGeneratorChain`.

    Attributes:
        lemmas: Generated vocabulary list.
    """

    lemmas: list[GeneratedLemma] = Field(default_factory=list)


def build_lemma_generator_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[LemmaGeneratorInput, LemmaGeneratorOutput]:
    """Build a lemma generator chain wired to `chat_config`."""
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "lemma_generator",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=LemmaGeneratorInput,
        output_model=LemmaGeneratorOutput,
    )
