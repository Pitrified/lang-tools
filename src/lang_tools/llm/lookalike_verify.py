"""LookalikeVerifyChain: classify look-alike pairs and write the trap note (phase 11).

The deterministic generator (`lexicon.ingestion.lookalikes`) finds word pairs
whose spelling resembles across two languages, with a provisional kind from the
wordnet senses. The senses are sparse and sometimes wrong outside English, so a
model makes the call. For a batch of pairs of one language pair, it decides
whether each is a ``full`` false friend, a ``partial`` one, a ``cognate`` or
``unrelated`` (a coincidental resemblance nobody would confuse), and for a false
friend writes a one-line English note a learner reads.

Output is generated content: a sampled review accepts a run, and only accepted
rows reach the build (``data/curated/lookalikes.jsonl``).
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

#: What the verifier may answer; ``unrelated`` means "no edge".
Verdict = Literal["full", "partial", "cognate", "unrelated"]


class PairSource(BaseModel):
    """One look-alike pair, as the prompt shows it.

    Attributes:
        key: The item key (``{target_id}:{known_id}``).
        target_word: The word in the language being learned.
        target_senses: Its main senses, most common first, as
            ``"gloss (English words)"`` strings joined with `` / ``.
        known_word: The word in the learner's known language.
        known_senses: Its main senses, in the same shape.
    """

    key: str
    target_word: str
    target_senses: str = ""
    known_word: str
    known_senses: str = ""


class LookalikeVerifyInput(BaseModelKwargs):
    """Inputs to `LookalikeVerifyChain`: a batch of one language pair's look-alikes.

    Attributes:
        target_language_name: The learned language's English name.
        known_language_name: The known language's English name.
        pairs: The pairs to classify.
    """

    target_language_name: str
    known_language_name: str
    pairs: list[PairSource] = Field(default_factory=list)


class KeyedVerdict(BaseModel):
    """The verdict on one pair.

    Attributes:
        key: The item key, echoed from the input.
        kind: ``full``, ``partial``, ``cognate`` or ``unrelated``.
        same_root: Whether the two words share an etymological root (prompt
            v5); None from an older prompt.
        note: For a false friend, one English line saying what each word means;
            empty otherwise.
    """

    key: str
    kind: Verdict
    same_root: bool | None = None
    note: str = ""


class LookalikeVerifyOutput(BaseModel):
    """Outputs from `LookalikeVerifyChain`.

    Attributes:
        verdicts: One verdict per input pair.
    """

    verdicts: list[KeyedVerdict] = Field(default_factory=list)


def build_lookalike_verify_chain(
    chat_config: ChatConfig,
    *,
    base_prompt_fol: Path | None = None,
    version: str = "auto",
) -> StructuredLLMChain[LookalikeVerifyInput, LookalikeVerifyOutput]:
    """Build a look-alike verification chain wired to `chat_config`."""
    return StructuredLLMChain(
        chat_config=chat_config,
        prompt_str=load_prompt(
            "lookalike_verify",
            base_prompt_fol=base_prompt_fol,
            version=version,
        ),
        input_model=LookalikeVerifyInput,
        output_model=LookalikeVerifyOutput,
    )
