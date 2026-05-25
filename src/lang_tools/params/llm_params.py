"""LLM params for lang-tools.

Loads chat config for the tutor and other LLM chains.
Currently uses FakeChatModelConfig (no API key required).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage
from llm_core.testing import FakeChatModelConfig
from loguru import logger as lg

if TYPE_CHECKING:
    from llm_core.chat.config.base import ChatConfig

_FAKE_TUTOR_RESPONSE = json.dumps({
    "correction": {
        "content": "",
        "translation": "",
        "errors": [],
    },
    "conversation": {
        "content": "Olá! Como vai você? Vamos conversar um pouco.",
        "translation": "Hello! How are you? Let's chat a bit.",
    },
})


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
            responses=[AIMessage(content=_FAKE_TUTOR_RESPONSE)],
        )
