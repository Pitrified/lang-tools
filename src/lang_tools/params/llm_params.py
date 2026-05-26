"""LLM params for lang-tools.

Loads chat config for the tutor and other LLM chains.
Currently uses FakeChatModelConfig (no API key required).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage
from llm_core.testing import FakeChatModelConfig
from loguru import logger as lg

from lang_tools.llm.tutor import ConversationBlock
from lang_tools.llm.tutor import CorrectionBlock
from lang_tools.llm.tutor import ErrorDetail
from lang_tools.llm.tutor import TutorOutput

if TYPE_CHECKING:
    from llm_core.chat.config.base import ChatConfig

_FAKE_TUTOR_OUTPUT = TutorOutput(
    correction=CorrectionBlock(
        content="Eu estou bem, não 'Eu é bem'.",
        translation="I am well, not 'I is well'.",
        errors=[
            ErrorDetail(
                original="Eu é bem",
                corrected="Eu estou bem",
                explanation="Use 'estar' (estou) for temporary states, not 'ser' (é).",
            ),
            ErrorDetail(
                original="Obrigado por perguntar",
                corrected="Obrigado por perguntar",
                explanation="Consider 'Obrigada' if the speaker is female.",
            ),
        ],
    ),
    conversation=ConversationBlock(
        content="Que bom! O que você fez hoje de interessante?",
        translation="That's good! What did you do today that was interesting?",
    ),
)


class LlmParams:
    """LLM configuration parameters.

    Provides chat configs for LLM chains used across lang-tools.
    Currently backed by FakeChatModelConfig for development without API keys.
    Swap to ChatOpenAIConfig when ready for real LLM calls.
    """

    def __init__(self) -> None:
        """Load LLM params."""
        lg.info("Loading LLM params (fake mode)")
        self._load_params()

    def _load_params(self) -> None:
        """Build chat configs."""
        self.tutor_chat_config: ChatConfig = FakeChatModelConfig(
            responses=[AIMessage(content=_FAKE_TUTOR_OUTPUT.model_dump_json())],
        )
