"""In-memory lemma store loaded from bootstrap CSV files.

Provides a simple read-only lemma repository that loads all CSV files from
`data/bootstrap/` at import time. Used by the webapp to serve lemma data
without requiring a database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg

from lang_tools.lexicon.ingestion.csv_loader import load_csv
from lang_tools.params.lang_tools_params import get_lang_tools_params

if TYPE_CHECKING:
    from lang_tools.lexicon.lemma import Lemma


def _load_all() -> list[Lemma]:
    """Load all bootstrap CSV files into a flat lemma list."""
    bootstrap_dir = get_lang_tools_params().paths.data_fol / "bootstrap"
    lemmas: list[Lemma] = []
    if not bootstrap_dir.exists():
        lg.warning("Bootstrap dir not found: {}", bootstrap_dir)
        return lemmas
    for csv_path in sorted(bootstrap_dir.glob("*.csv")):
        batch = list(load_csv(csv_path))
        lg.info("Loaded {} lemmas from {}", len(batch), csv_path.name)
        lemmas.extend(batch)
    lg.info("Lemma store initialized: {} total lemmas", len(lemmas))
    return lemmas


_ALL_LEMMAS: list[Lemma] = _load_all()
_LEMMAS_BY_ID: dict[str, Lemma] = {lemma.id: lemma for lemma in _ALL_LEMMAS}


def get_all_lemmas() -> list[Lemma]:
    """Return all bootstrap lemmas."""
    return _ALL_LEMMAS


def get_lemma_by_id(lemma_id: str) -> Lemma | None:
    """Lookup a lemma by its deterministic ID."""
    return _LEMMAS_BY_ID.get(lemma_id)


def get_lemmas_by_language(language: str) -> list[Lemma]:
    """Filter lemmas by language code."""
    return [lemma for lemma in _ALL_LEMMAS if lemma.language == language]


def get_lemmas_by_topic(topic: str) -> list[Lemma]:
    """Filter lemmas containing a given topic tag."""
    return [lemma for lemma in _ALL_LEMMAS if topic in lemma.topics]


def get_lemmas_filtered(
    language: str | None = None,
    topic: str | None = None,
) -> list[Lemma]:
    """Filter lemmas by language and/or topic."""
    results = _ALL_LEMMAS
    if language:
        results = [lemma for lemma in results if lemma.language == language]
    if topic:
        results = [lemma for lemma in results if topic in lemma.topics]
    return results
