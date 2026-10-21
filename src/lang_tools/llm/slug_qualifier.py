"""SlugQualifierChain: pick gloss-derived qualifiers for colliding slugs (phase 8).

Concept ids are ``c__{slug}__{hash}``. After 5.55's deterministic lexfile tier,
9,782 groups of concepts still share a slug (``hot-adj-all`` names 20 senses of
"hot"). The hash keeps the ids unique; the qualifier only makes them legible, so a
human can tell ``hot-temperature`` from ``hot-stolen-smuggled`` without the gloss.

The chain sees a whole collision group at once, so the qualifiers it picks can be
told apart from each other, and the prompt restricts every qualifier word to the
concept's own English gloss - the property `lexicon.slug_qualifiers` checks before
accepting anything, so the job cannot invent meaning into an id.
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


class QualifierCandidate(BaseModel):
    """One concept of a collision group, as the prompt shows it.

    Attributes:
        key: The concept's stable key (`concept_id.concept_key`).
        gloss: The concept's English gloss - the only source of qualifier words.
        members: The concept's English member forms, comma-joined (context).
    """

    key: str
    gloss: str
    members: str = ""


class SlugQualifierInput(BaseModelKwargs):
    """Inputs to `SlugQualifierChain`: one collision group.

    Attributes:
        slug: The slug the group shares (tier 1, e.g. ``hot-adj-all``).
        base: The tier-0 base word the slug starts from (e.g. ``hot``).
        concepts: The group's concepts.
    """

    slug: str
    base: str
    concepts: list[QualifierCandidate] = Field(default_factory=list)


class KeyedQualifier(BaseModel):
    """One concept's qualifier.

    Attributes:
        key: The concept key, echoed from the input.
        qualifier: 1-3 words taken from the concept's gloss.
    """

    key: str
    qualifier: str


class SlugQualifierOutput(BaseModel):
    """Outputs from `SlugQualifierChain`.

    Attributes:
        qualifiers: One qualifier per input concept.
    """

    qualifiers: list[KeyedQualifier] = Field(default_factory=list)


def build_slug_qualifier_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[SlugQualifierInput, SlugQualifierOutput]:
    """Build a slug qualifier chain wired to `chat_config`."""
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "slug_qualifier",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=SlugQualifierInput,
        output_model=SlugQualifierOutput,
    )
