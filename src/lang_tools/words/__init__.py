"""Canonical word data model and ingestion pipelines.

Public API:
    Word: unified word entity.
    Gloss, GlossExample, WordExample, FalseFriend: supporting types.
    FrequencyLevel: literal type for word frequency.
    word_id: deterministic ID for a (text, language) pair.
"""

from lang_tools.words.word import FalseFriend
from lang_tools.words.word import FrequencyLevel
from lang_tools.words.word import Gloss
from lang_tools.words.word import GlossExample
from lang_tools.words.word import Word
from lang_tools.words.word import WordExample
from lang_tools.words.word_id import word_id

__all__ = [
    "FalseFriend",
    "FrequencyLevel",
    "Gloss",
    "GlossExample",
    "Word",
    "WordExample",
    "word_id",
]
