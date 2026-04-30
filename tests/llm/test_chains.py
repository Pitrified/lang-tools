"""Tests for `lang_tools.llm` chain factories.

These only verify that the in-package prompts match the input model fields
(the eager validation in `StructuredLLMChain.__post_init__`). No real API
calls are made.
"""

from llm_core.chat.config.openai import ChatOpenAIConfig
from pydantic import SecretStr

from lang_tools.llm import build_conversation_chain
from lang_tools.llm import build_greeting_chain
from lang_tools.llm import build_paragraph_splitter_chain
from lang_tools.llm import build_topic_suggestion_chain
from lang_tools.llm import build_translation_chain
from lang_tools.llm import build_tutor_chain
from lang_tools.llm import build_word_generator_chain


def _cfg() -> ChatOpenAIConfig:
    return ChatOpenAIConfig(api_key=SecretStr("dummy"))


def test_build_translation_chain() -> None:
    build_translation_chain(_cfg())


def test_build_conversation_chain() -> None:
    build_conversation_chain(_cfg())


def test_build_tutor_chain() -> None:
    build_tutor_chain(_cfg())


def test_build_topic_suggestion_chain() -> None:
    build_topic_suggestion_chain(_cfg())


def test_build_paragraph_splitter_chain() -> None:
    build_paragraph_splitter_chain(_cfg())


def test_build_greeting_chain() -> None:
    build_greeting_chain(_cfg())


def test_build_word_generator_chain() -> None:
    build_word_generator_chain(_cfg())
