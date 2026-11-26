"""Reviewed shared meanings: flag a false friend whose main meaning is shared.

A false friend's card hint carries what the look-alike mainly means
(`LookalikeHint.means`), and a drill that asks in another language can offer
those words as a trap: pt *bravo* "angry" gets *good* from it *bravo*. For a
``partial`` false friend that main meaning is often one the pt word has too:
it *tardi* mainly means "late", and so can pt *tarde* (mostly "afternoon"), so
*late* is no trap. No rule over the senses tells these apart, so a review of
each pair, full or partial, answers whether Portuguese speakers use the pt word
for the look-alike's main meaning:

- `SharedMeaningRow` is one reviewed verdict on a look-alike pair; ``s`` says the
  pt word is used for the look-alike's main meaning, ``d`` says it is not, ``w``
  says the main meaning the card shows is itself wrong (no flag; the log lists
  the pair for a later fix);
- the committed ``data/curated/shared_meaning_log.jsonl`` holds the rows, and only
  the latest row of a pair counts, so a later ``d`` retracts an ``s``;
- `apply_shared_meanings` runs as a build stage and sets
  `LookalikeRelation.shares_main_meaning` on the edge of each ``s`` row, which
  the card's `LookalikeHint.shares_meaning` carries.

A row whose pair has no false-friend edge in the build (the edge was dropped, or
it is a cognate, which shares its meaning by definition) is counted as stale and
skipped, never fatal (the curated-input rule).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Literal

from loguru import logger as lg
from pydantic import BaseModel

from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.relations import (
    LookalikeKind,  # noqa: TC001 - pydantic field type
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from lang_tools.lexicon.relations import LookalikeRelation

#: Committed curated review log, under ``<data_fol>/curated/``.
SHARED_MEANING_LOG_FILE = "shared_meaning_log.jsonl"


class SharedMeaningRow(BaseModel):
    """One reviewed shared-meaning verdict (a JSONL line).

    Attributes:
        batch: The review batch that wrote the row.
        target_id: The pt word's lemma id.
        target_text: The pt word (review aid).
        known_id: The look-alike's lemma id.
        known_text: The look-alike (review aid).
        known_language: The look-alike's language.
        kind: The edge's kind when reviewed (review aid).
        label: ``s`` the pt word is also used for the look-alike's main
            meaning, ``d`` it is not, ``w`` the main meaning shown is wrong.
        edge_case: The reviewer marked the item with ``!``.
        reason: The reviewer's reason.
        model: The reviewer (an agent tag or ``manual``).
        rulebook_sha: Hash of the rulebook the batch was labelled against.
    """

    batch: str
    target_id: str
    target_text: str = ""
    known_id: str
    known_text: str = ""
    known_language: str = ""
    kind: LookalikeKind
    label: Literal["s", "d", "w"]
    edge_case: bool = False
    reason: str = ""
    model: str = ""
    rulebook_sha: str = ""

    @property
    def pair(self) -> tuple[str, str]:
        """The two lemma ids sorted, as the edge stores them."""
        first, second = sorted((self.target_id, self.known_id))
        return first, second


def load_shared_meanings(data_fol: Path) -> list[SharedMeaningRow]:
    """Read the latest row per look-alike pair, if any.

    Args:
        data_fol: Project data folder.

    Returns:
        One row per pair, the latest written; empty when the file does not
        exist.
    """
    path = curated_path(data_fol, SHARED_MEANING_LOG_FILE)
    if not path.exists():
        return []
    latest: dict[tuple[str, str], SharedMeaningRow] = {}
    for row in read_jsonl(SharedMeaningRow, path):
        latest.pop(row.pair, None)
        latest[row.pair] = row
    return list(latest.values())


def apply_shared_meanings(
    edges: Iterable[LookalikeRelation], rows: Iterable[SharedMeaningRow]
) -> tuple[int, int]:
    """Set `LookalikeRelation.shares_main_meaning` on the reviewed edges, in place.

    Args:
        edges: Every look-alike edge of the build.
        rows: The latest row per pair, typically from `load_shared_meanings`.

    Returns:
        ``(flagged, stale)``: edges flagged, and rows whose pair has no
        false-friend edge in the build. A ``d`` or ``w`` row on a live edge sets
        nothing and counts as neither.
    """
    by_pair = {(edge.lemma_id_a, edge.lemma_id_b): edge for edge in edges}
    flagged = stale = 0
    for row in rows:
        edge = by_pair.get(row.pair)
        if edge is None or not edge.is_false_friend:
            stale += 1
            continue
        if row.label == "s":
            edge.shares_main_meaning = True
            flagged += 1
    lg.info("Shared meanings: {} flagged, {} stale", flagged, stale)
    return flagged, stale
