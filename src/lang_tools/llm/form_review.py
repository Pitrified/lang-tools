"""FormReviewChain: classify a suspicious wordnet member form (phase 8).

931 non-English member forms are five words or longer, or over 40 characters.
Most are legitimate (proper names, multiword terms); a few are definitions,
text in the wrong language, or garbled strings that reached the corpus as
lemmas. The chain proposes a verdict per form; nothing it says is applied until a
human accepts it (see `lexicon.ingestion.form_review`).
"""

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

FormKind = Literal["term", "name", "definition", "wrong language", "garbled"]


class FormReviewInput(BaseModelKwargs):
    """Inputs to `FormReviewChain`: one member form with its concept context.

    Attributes:
        language: ISO 639-1 code of the form.
        form: The member form under review.
        english_definition: The concept's English gloss.
        english_members: The concept's English member forms.
        other_forms: The concept's other member forms in `language`.
    """

    language: str
    form: str
    english_definition: str = ""
    english_members: list[str] = Field(default_factory=list)
    other_forms: list[str] = Field(default_factory=list)


class FormReviewOutput(BaseModel):
    """Outputs from `FormReviewChain`.

    Attributes:
        kind: What the form is.
        drop: Whether it should leave the corpus.
        reason: One short English sentence.
    """

    kind: FormKind
    drop: bool
    reason: str = ""


def build_form_review_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[FormReviewInput, FormReviewOutput]:
    """Build a form review chain wired to `chat_config`."""
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "form_review",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=FormReviewInput,
        output_model=FormReviewOutput,
    )
