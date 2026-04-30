"""ParagraphSplitterChain: split text into reconstruction-friendly portions."""

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


class SplitterInput(BaseModelKwargs):
    """Inputs to `ParagraphSplitterChain`.

    Attributes:
        text: Text to split.
        language: ISO 639-1 code of the source language.
    """

    text: str
    language: str


class SplitterOutput(BaseModel):
    """Outputs from `ParagraphSplitterChain`.

    Attributes:
        portions: Ordered list of split portions.
    """

    portions: list[str] = Field(default_factory=list)


def build_paragraph_splitter_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[SplitterInput, SplitterOutput]:
    """Build a paragraph splitter chain wired to `chat_config`."""
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "paragraph_splitter",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=SplitterInput,
        output_model=SplitterOutput,
    )
