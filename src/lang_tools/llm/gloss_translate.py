"""GlossTranslateChain: write non-English glosses from the English one (phase 8).

OMW carries English glosses for every concept and almost none in the other four
languages (fr / pt / es 0%, it 5.5%). This chain renders the English gloss into the
target language for a batch of concepts at once - one request per ~25 concepts of
one language, so the instructions and schema are paid once per batch rather than
once per gloss - grounded in the concept's member words in both languages.

Output is generated content: `lexicon.ingestion.gloss_backfill` checks it, a
sampled human review accepts a run, and every gloss it produces is tagged ``llm``
in `Concept.definition_sources`.
"""

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


class GlossSource(BaseModel):
    """One concept to gloss, as the prompt shows it.

    Attributes:
        key: The item key (``{language}:{concept_key}``).
        english_definition: The concept's English gloss.
        english_members: The concept's English words, comma-joined.
        target_members: The concept's words in the target language, comma-joined.
    """

    key: str
    english_definition: str
    english_members: str = ""
    target_members: str = ""


class GlossTranslateInput(BaseModelKwargs):
    """Inputs to `GlossTranslateChain`: a batch of one language's concepts.

    Attributes:
        language_name: The target language's English name (``"Portuguese"``).
        concepts: The concepts to gloss.
    """

    language_name: str
    concepts: list[GlossSource] = Field(default_factory=list)


class KeyedGloss(BaseModel):
    """One generated gloss.

    Attributes:
        key: The item key, echoed from the input.
        definition: The gloss in the target language.
    """

    key: str
    definition: str


class GlossTranslateOutput(BaseModel):
    """Outputs from `GlossTranslateChain`.

    Attributes:
        glosses: One gloss per input concept.
    """

    glosses: list[KeyedGloss] = Field(default_factory=list)


def build_gloss_translate_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[GlossTranslateInput, GlossTranslateOutput]:
    """Build a gloss translation chain wired to `chat_config`."""
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "gloss_translate",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=GlossTranslateInput,
        output_model=GlossTranslateOutput,
    )
