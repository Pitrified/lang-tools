"""Reviewed best senses: pin the meaning a lemma's card shows.

A card shows its lemma's best sense, picked by frequency, then by concept
commonness. Outside English every sense of a lemma ties on frequency (the SemCor
prior is English-only), so commonness decides, and a common concept that the
lemma reaches only through a rare reading wins: pt *homens* shows "work force",
*bem* "kind of". No rule tells those apart from the right pick, so a review does:

- `BestSense` is one reviewed row, keyed on ``lemma_id`` and `concept_key`, both
  stable across rebuilds and re-slugs (as in `form_review.FormDrop`);
- the committed ``data/curated/best_senses.jsonl`` holds the rows, and only the
  latest row of a lemma counts, so a later row with no concept retracts an
  earlier pin;
- `apply_best_senses` runs as a build stage and sets `Sense.is_best`, which the
  card's best-sense pick orders first.

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

#: Committed curated best-sense pins, under ``<data_fol>/curated/``.
BEST_SENSES_FILE = "best_senses.jsonl"


class BestSense(BaseModel):
    """One reviewed best-sense verdict (a JSONL line).

    Attributes:
        lemma_id: The reviewed lemma.
        concept_key: The pinned sense's concept (`concept_key`), or ``None`` to
            keep the frequency pick (and retract an earlier pin).
        lemma_text: The lemma's text (review aid).
        language: The lemma's language.
        status: ``proposed`` until accepted; only ``accepted`` rows apply.
        model: The reviewer (an agent tag or a model name).
        prompt_sha: Hash of the rulebook the reviewer followed.
        batch: The review batch that wrote the row.
        edge_case: The reviewer flagged the item as a judgement call.
    """

    lemma_id: str
    concept_key: str | None = None
    lemma_text: str = ""
    language: str = ""
    status: ReviewStatus = "proposed"
    model: str = ""
    prompt_sha: str = ""
    batch: str = ""
    edge_case: bool = False


def load_best_senses(data_fol: Path) -> list[BestSense]:
    """Read the latest accepted row per lemma of the committed file, if any.

    Args:
        data_fol: Project data folder.

    Returns:
        One row per lemma whose latest row is accepted; empty when the file
        does not exist.
    """
    path = curated_path(data_fol, BEST_SENSES_FILE)
    if not path.exists():
        return []
    latest: dict[str, BestSense] = {}
    for row in read_jsonl(BestSense, path):
        latest.pop(row.lemma_id, None)
        latest[row.lemma_id] = row
    return [row for row in latest.values() if row.status == "accepted"]


def apply_best_senses(
    senses: Iterable[Sense], rows: Iterable[BestSense]
) -> tuple[int, int]:
    """Set `Sense.is_best` on the pinned senses, in place.

    Args:
        senses: Every sense of the build (after the member-form drops).
        rows: Accepted rows, typically from `load_best_senses`.

    Returns:
        ``(applied, stale)``: pins set, and pinning rows whose sense the build
        does not have. A row with no concept keeps the frequency pick and
        counts as neither.
    """
    by_key = {
        (sense.lemma_id, concept_key(sense.concept_id)): sense for sense in senses
    }
    applied = stale = 0
    for row in rows:
        if row.concept_key is None:
            continue
        sense = by_key.get((row.lemma_id, row.concept_key))
        if sense is None:
            stale += 1
            continue
        sense.is_best = True
        applied += 1
    lg.info("Best senses: {} pinned, {} stale", applied, stale)
    return applied, stale
