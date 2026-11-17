"""Reviewed lead translations: pick the first word a card shows for a concept.

A card lists a concept's words in each translation language by frequency, and
drills pair the first one. The frequency is the word's surface count split over
its senses, so an en noun that is also a frequent verb form keeps the verb's
count: *calling* (its only noun sense) leads *career* (split over three) on pt
*carreira*'s card, and *being* leads *existence* on *existência*. Most -ing leads
are right (*building*, *meeting*), so no rule tells them apart; a review does:

- `LeadTranslation` is one reviewed row, keyed on `concept_key` and
  ``language``, so a concept has at most one lead per language;
- the committed ``data/curated/lead_translations.jsonl`` holds the rows, and only
  the latest row of a key counts, so a later row with no lemma retracts a lead;
- `apply_lead_translations` runs as a build stage and sets `Sense.is_lead`, which
  the card's translations put first.

A row naming a lemma or a concept the build does not have is counted as stale and
skipped, never fatal (the curated-input rule).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg
from pydantic import BaseModel

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.maintenance import ReviewStatus
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from lang_tools.lexicon.sense import Sense

#: Committed curated lead translations, under ``<data_fol>/curated/``.
LEAD_TRANSLATIONS_FILE = "lead_translations.jsonl"


class LeadTranslation(BaseModel):
    """One reviewed lead-translation verdict (a JSONL line).

    Attributes:
        concept_key: The concept whose words are ordered (`concept_key`).
        language: The language of the words.
        lemma_id: The lemma that leads, or ``None`` to keep the frequency order
            (and retract an earlier lead).
        word: The leading lemma's text (review aid).
        card_word: The word of the card the review was asked about (review aid).
        status: ``proposed`` until accepted; only ``accepted`` rows apply.
        model: The reviewer (an agent tag or ``manual``).
        prompt_sha: Hash of the rulebook the reviewer followed.
        batch: The review batch that wrote the row.
    """

    concept_key: str
    language: str
    lemma_id: str | None = None
    word: str = ""
    card_word: str = ""
    status: ReviewStatus = "proposed"
    model: str = ""
    prompt_sha: str = ""
    batch: str = ""

    @property
    def key(self) -> str:
        """The row key, ``{concept_key}:{language}``."""
        return f"{self.concept_key}:{self.language}"


def load_lead_translations(data_fol: Path) -> list[LeadTranslation]:
    """Read the latest accepted row per concept and language, if any.

    Args:
        data_fol: Project data folder.

    Returns:
        One row per key whose latest row is accepted; empty when the file does
        not exist.
    """
    path = curated_path(data_fol, LEAD_TRANSLATIONS_FILE)
    if not path.exists():
        return []
    latest: dict[str, LeadTranslation] = {}
    for row in read_jsonl(LeadTranslation, path):
        latest.pop(row.key, None)
        latest[row.key] = row
    return [row for row in latest.values() if row.status == "accepted"]


def apply_lead_translations(
    senses: Iterable[Sense], rows: Iterable[LeadTranslation]
) -> tuple[int, int]:
    """Set `Sense.is_lead` on the reviewed leads, in place.

    The row's language is not checked against the lemma: a lemma id is derived
    from its word and language, so a sense found by lemma and concept is in the
    row's language unless the row was mistyped, and the review tool writes both
    from the same lemma.

    Args:
        senses: Every sense of the build (after the member-form drops).
        rows: Accepted rows, typically from `load_lead_translations`.

    Returns:
        ``(applied, stale)``: leads set, and leading rows whose sense the build
        does not have. A row with no lemma keeps the frequency order and counts
        as neither.
    """
    by_key = {
        (sense.lemma_id, concept_key(sense.concept_id)): sense for sense in senses
    }
    applied = stale = 0
    for row in rows:
        if row.lemma_id is None:
            continue
        sense = by_key.get((row.lemma_id, row.concept_key))
        if sense is None:
            stale += 1
            continue
        sense.is_lead = True
        applied += 1
    lg.info("Lead translations: {} set, {} stale", applied, stale)
    return applied, stale
