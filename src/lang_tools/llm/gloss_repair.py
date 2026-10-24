"""GlossRepairChain: rewrite a thin `definition == lemma` gloss (phase 05.55).

Drafts a fuller replacement for a gloss that merely restates the concept's sole
member form, grounded strictly in the synset context (member forms, English
gloss and members, lexfile, hypernym gloss) so it cannot invent meaning. The
output is a **proposal**: it flows into the reviewable JSONL of
`lang_tools.lexicon.maintenance` and is applied only after human acceptance.
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


class GlossRepairInput(BaseModelKwargs):
    """Inputs to `GlossRepairChain` (one thin-gloss worklist entry).

    Attributes:
        language: ISO 639-1 code of the gloss to rewrite.
        current_definition: The thin gloss (equals the sole member form).
        member_forms: The concept's member form(s) in `language`.
        english_definition: The concept's English gloss, if any.
        english_members: The concept's English member forms.
        lexfile: WordNet lexicographer class (e.g. ``noun.cognition``), if any.
        hypernym_definition: English gloss of a hypernym concept, if any.
    """

    language: str
    current_definition: str
    member_forms: list[str] = Field(default_factory=list)
    english_definition: str | None = None
    english_members: list[str] = Field(default_factory=list)
    lexfile: str | None = None
    hypernym_definition: str | None = None


class GlossRepairOutput(BaseModel):
    """Outputs from `GlossRepairChain`.

    Attributes:
        proposed_definition: The replacement gloss in the target language.
        rationale: One English sentence on how the context grounds the gloss.
    """

    proposed_definition: str
    rationale: str = ""


def build_gloss_repair_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[GlossRepairInput, GlossRepairOutput]:
    """Build a gloss repair chain wired to `chat_config`."""
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "gloss_repair",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=GlossRepairInput,
        output_model=GlossRepairOutput,
    )
