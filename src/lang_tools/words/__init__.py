"""Canonical word data model, ingestion pipelines, and read/query helpers.

Public API:
    Word: unified word entity.
    Gloss, GlossExample, WordExample, FalseFriend: supporting types.
    FrequencyLevel: literal type for word frequency.
    word_id: deterministic ID for a (text, language) pair.
    get_all_words, get_word_by_id, get_words_by_language, get_words_by_topic,
        get_words_filtered: read/query helpers over the on-disk word store.

The read/query helpers are the stable surface ``lang-tutor`` imports to pull
the word pool it drills the user on. Importing this subpackage loads the
bootstrap content from disk (see `lang_tools.words.word_store`).
"""

from lang_tools.words.word import FalseFriend
from lang_tools.words.word import FrequencyLevel
from lang_tools.words.word import Gloss
from lang_tools.words.word import GlossExample
from lang_tools.words.word import Word
from lang_tools.words.word import WordExample
from lang_tools.words.word_id import word_id
from lang_tools.words.word_store import get_all_words
from lang_tools.words.word_store import get_word_by_id
from lang_tools.words.word_store import get_words_by_language
from lang_tools.words.word_store import get_words_by_topic
from lang_tools.words.word_store import get_words_filtered

__all__ = [
    "FalseFriend",
    "FrequencyLevel",
    "Gloss",
    "GlossExample",
    "Word",
    "WordExample",
    "get_all_words",
    "get_word_by_id",
    "get_words_by_language",
    "get_words_by_topic",
    "get_words_filtered",
    "word_id",
]
