"""TopicSuggestionChain: generate practice topics for a language."""

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


class TopicSuggestionInput(BaseModelKwargs):
    """Inputs to `TopicSuggestionChain`.

    Attributes:
        language: ISO 639-1 target language code.
        difficulty_level: ``"beginner"`` / ``"intermediate"`` / ``"advanced"``.
        num_topics: How many topics to return.
        exclude_topics: Topics to avoid (de-duplication).
    """

    language: str
    difficulty_level: str = "intermediate"
    num_topics: int = 5
    exclude_topics: list[str] = Field(default_factory=list)


class TopicSuggestionOutput(BaseModel):
    """Outputs from `TopicSuggestionChain`.

    Attributes:
        topics: List of topic strings.
    """

    topics: list[str] = Field(default_factory=list)


def build_topic_suggestion_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[TopicSuggestionInput, TopicSuggestionOutput]:
    """Build a topic suggestion chain wired to `chat_config`."""
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "topic_suggestion",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=TopicSuggestionInput,
        output_model=TopicSuggestionOutput,
    )
