"""In-memory word store loaded from bootstrap CSV files.

Provides a simple read-only word repository that loads all CSV files from
`data/bootstrap/` at import time. Used by the webapp to serve word data
without requiring a database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.params.lang_tools_params import get_lang_tools_params
from lang_tools.words.ingestion.csv_loader import load_csv

if TYPE_CHECKING:
    from lang_tools.words.word import Word


def _load_all() -> list[Word]:
    """Load all bootstrap CSV files into a flat word list."""
    bootstrap_dir = get_lang_tools_params().paths.data_fol / "bootstrap"
    words: list[Word] = []
    if not bootstrap_dir.exists():
        lg.warning("Bootstrap dir not found: {}", bootstrap_dir)
        return words
    for csv_path in sorted(bootstrap_dir.glob("*.csv")):
        batch = list(load_csv(csv_path))
        lg.info("Loaded {} words from {}", len(batch), csv_path.name)
        words.extend(batch)
    lg.info("Word store initialized: {} total words", len(words))
    return words


_ALL_WORDS: list[Word] = _load_all()
_BY_ID: dict[str, Word] = {w.id: w for w in _ALL_WORDS}


def get_all_words() -> list[Word]:
    """Return all bootstrap words."""
    return _ALL_WORDS


def get_word_by_id(word_id: str) -> Word | None:
    """Lookup a word by its deterministic ID."""
    return _BY_ID.get(word_id)


def get_words_by_language(language: str) -> list[Word]:
    """Filter words by language code."""
    return [w for w in _ALL_WORDS if w.language == language]


def get_words_by_topic(topic: str) -> list[Word]:
    """Filter words containing a given topic tag."""
    return [w for w in _ALL_WORDS if topic in w.topics]


def get_words_filtered(
    language: str | None = None,
    topic: str | None = None,
) -> list[Word]:
    """Filter words by language and/or topic."""
    results = _ALL_WORDS
    if language:
        results = [w for w in results if w.language == language]
    if topic:
        results = [w for w in results if topic in w.topics]
    return results
