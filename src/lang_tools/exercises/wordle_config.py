"""Wordle exercise configuration.

This module defines ``WordleConfig``, which carries the exercise-level
settings for a Wordle game session. It follows the Config side of the
project's Config / Params pattern: field defaults are the single canonical
place where the values ``[4, 5, 6, 7]`` and ``5`` are defined. No Params
class is needed because there are no environment variables or secrets to
load.

Callers instantiate ``WordleConfig`` directly, with or without overrides:

Example:
    Default settings::

        config = WordleConfig()

    Five-letter-only variant::

        config = WordleConfig(word_lengths=[5], default_word_length=5)
"""

from __future__ import annotations

from pydantic import Field

from lang_tools.data_models.basemodel_kwargs import BaseModelKwargs


class WordleConfig(BaseModelKwargs):
    """Configuration for a Wordle exercise session.

    Attributes:
        word_lengths:
            Allowed word lengths offered in the word-length selector.
            Defaults to ``[4, 5, 6, 7]``.
        default_word_length:
            Pre-selected word length when no user preference is stored.
            Defaults to ``5``.
    """

    word_lengths: list[int] = Field(default_factory=lambda: [4, 5, 6, 7])
    default_word_length: int = 5
