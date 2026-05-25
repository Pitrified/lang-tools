"""Tutor service bridging the LLM chain to the exercise API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.exercises.conversational_tutor import TutorMessage
from lang_tools.llm.tutor import TutorInput
from lang_tools.llm.tutor import TutorOutput
from lang_tools.llm.tutor import build_tutor_chain
from lang_tools.params.lang_tools_params import get_llm_params

if TYPE_CHECKING:
    from llm_core.chains.structured_chain import StructuredLLMChain

_chain: StructuredLLMChain[TutorInput, TutorOutput] | None = None


def _get_chain() -> StructuredLLMChain[TutorInput, TutorOutput]:
    """Lazy-init the tutor chain from central params."""
    global _chain  # noqa: PLW0603
    if _chain is None:
        llm_params = get_llm_params()
        _chain = build_tutor_chain(chat_config=llm_params.tutor_chat_config)
    return _chain


def tutor_reply(
    user_text: str,
    history: list[TutorMessage],
    *,
    language: str = "pt",
    topic: str = "",
) -> TutorMessage:
    """Call the LLM tutor chain and return a TutorMessage.

    Args:
        user_text: User's message in the target language.
        history: Conversation history so far.
        language: Target language code.
        topic: Conversation topic.

    Returns:
        TutorMessage with the tutor's reply.
    """
    chain_input = TutorInput(
        topic=topic or "general conversation",
        language=language,
        user_message=user_text,
        history=history,
    )
    result: TutorOutput = _get_chain().invoke(chain_input)
    lg.debug("Tutor reply: {}", result.conversation.content[:80])

    correction_text = (
        result.correction.content if result.correction.content.strip() else None
    )
    return TutorMessage(
        role="tutor",
        content=result.conversation.content,
        translation=result.conversation.translation or None,
        correction=correction_text,
    )
