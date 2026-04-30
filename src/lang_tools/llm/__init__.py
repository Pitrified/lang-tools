"""LLM service layer built on `llm-core`'s `StructuredLLMChain`.

Each module exposes a typed input model, a typed output model, and a
``build_*_chain(chat_config, base_prompt_fol=...)`` factory that loads the
versioned Jinja prompt and wires everything into a `StructuredLLMChain`.

Public API:
    TranslationInput, TranslationOutput, build_translation_chain
    ConversationInput, ConversationOutput, ConversationTurn,
        build_conversation_chain
    TutorInput, TutorOutput, CorrectionBlock, ConversationBlock, ErrorDetail,
        build_tutor_chain
    TopicSuggestionInput, TopicSuggestionOutput, build_topic_suggestion_chain
    SplitterInput, SplitterOutput, build_paragraph_splitter_chain
    GreetingInput, GreetingOutput, build_greeting_chain
    WordGeneratorInput, WordGeneratorOutput, GeneratedWord, build_word_generator_chain
"""

from lang_tools.llm.conversation import ConversationInput
from lang_tools.llm.conversation import ConversationOutput
from lang_tools.llm.conversation import ConversationTurn
from lang_tools.llm.conversation import build_conversation_chain
from lang_tools.llm.greeting import GreetingInput
from lang_tools.llm.greeting import GreetingOutput
from lang_tools.llm.greeting import build_greeting_chain
from lang_tools.llm.splitter import SplitterInput
from lang_tools.llm.splitter import SplitterOutput
from lang_tools.llm.splitter import build_paragraph_splitter_chain
from lang_tools.llm.topics import TopicSuggestionInput
from lang_tools.llm.topics import TopicSuggestionOutput
from lang_tools.llm.topics import build_topic_suggestion_chain
from lang_tools.llm.translation import TranslationInput
from lang_tools.llm.translation import TranslationOutput
from lang_tools.llm.translation import build_translation_chain
from lang_tools.llm.tutor import ConversationBlock
from lang_tools.llm.tutor import CorrectionBlock
from lang_tools.llm.tutor import ErrorDetail
from lang_tools.llm.tutor import TutorInput
from lang_tools.llm.tutor import TutorOutput
from lang_tools.llm.tutor import build_tutor_chain
from lang_tools.llm.word_generator import GeneratedWord
from lang_tools.llm.word_generator import WordGeneratorInput
from lang_tools.llm.word_generator import WordGeneratorOutput
from lang_tools.llm.word_generator import build_word_generator_chain

__all__ = [
    "ConversationBlock",
    "ConversationInput",
    "ConversationOutput",
    "ConversationTurn",
    "CorrectionBlock",
    "ErrorDetail",
    "GeneratedWord",
    "GreetingInput",
    "GreetingOutput",
    "SplitterInput",
    "SplitterOutput",
    "TopicSuggestionInput",
    "TopicSuggestionOutput",
    "TranslationInput",
    "TranslationOutput",
    "TutorInput",
    "TutorOutput",
    "WordGeneratorInput",
    "WordGeneratorOutput",
    "build_conversation_chain",
    "build_greeting_chain",
    "build_paragraph_splitter_chain",
    "build_topic_suggestion_chain",
    "build_translation_chain",
    "build_tutor_chain",
    "build_word_generator_chain",
]
