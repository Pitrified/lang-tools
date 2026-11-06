"""Reviewed sense additions: link a lemma to a concept the sources missed.

The card-sense review can keep, pin or drop the senses a lemma has, but some
frequent words lack the one they are used in: pt *sim* is linked only to "yea"
("not only so, but"), *vinte* only to wrong concepts, so the review removed it.
A sense addition is the reviewed fix:

- `SenseAddition` is one row, keyed on ``lemma_id`` and `concept_key` like a
  `form_review.FormDrop`, both stable across rebuilds and re-slugs;
- the committed ``data/curated/sense_additions.jsonl`` holds the rows, and only
  the latest row of a key counts, so a later ``add: false`` row retracts one;
- `apply_sense_additions` runs as a build stage right after the drops, so an
  addition wins over a drop of the same link and every later stage (frequency,
  CEFR, topics, look-alikes, best-sense pins) sees the new sense. A lemma the
  build lacks is created, so a word the review removed comes back.

A row may carry a `form_note`: an inflected form linked to its base word's
concept (pt *são* on "be") says which form it is, and the card shows it.

A row naming a concept the build does not have, or whose word does not give its
``lemma_id``, is counted as stale and skipped, never fatal (the curated-input
rule).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger as lg
from pydantic import BaseModel

from lang_tools.lexicon.concept_id import concept_key
from lang_tools.lexicon.ingestion.transform import SOURCE_MANUAL
from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.maintenance import ReviewStatus
from lang_tools.lexicon.maintenance import curated_path
from lang_tools.lexicon.maintenance import read_jsonl
from lang_tools.lexicon.sense import Sense

if TYPE_CHECKING:
    from pathlib import Path

    from lang_tools.lexicon.ingestion.transform import TaggedTables

#: Committed curated sense additions, under ``<data_fol>/curated/``.
SENSE_ADDITIONS_FILE = "sense_additions.jsonl"

#: Lexfile class -> the lemma part-of-speech label, for a lemma an addition creates.
_LEXFILE_POS = {"noun": "noun", "verb": "verb", "adj": "adjective", "adv": "adverb"}


class SenseAddition(BaseModel):
    """One reviewed link from a lemma to a concept (a JSONL line).

    Attributes:
        lemma_id: The lemma, ``lemma_id(word, language)``.
        concept_key: The linked concept (`concept_key`).
        word: The lemma's text, exactly as stored; used to create the lemma
            when the build lacks it.
        language: The lemma's language.
        add: True to add the link; a later False row retracts it.
        form_note: Which form of the word the sense is (see the module
            docstring); empty when the lemma is not an inflected form.
        reason: Why the link is right.
        status: ``proposed`` until accepted; only ``accepted`` rows apply.
        model: The reviewer (an agent tag, or ``manual``).
        prompt_sha: Hash of the rulebook the reviewer followed.
        batch: The review batch that wrote the row.
    """

    lemma_id: str
    concept_key: str
    word: str
    language: str
    add: bool = True
    form_note: str = ""
    reason: str = ""
    status: ReviewStatus = "proposed"
    model: str = ""
    prompt_sha: str = ""
    batch: str = ""

    @property
    def key(self) -> str:
        """The row key, ``{lemma_id}:{concept_key}``."""
        return f"{self.lemma_id}:{self.concept_key}"


def load_sense_additions(data_fol: Path) -> list[SenseAddition]:
    """Return the latest row per key of the committed file, if accepted.

    Only the newest row of a (``lemma_id``, `concept_key`) pair counts, so a
    later ``add: false`` row retracts an earlier addition.
    """
    path = curated_path(data_fol, SENSE_ADDITIONS_FILE)
    if not path.exists():
        return []
    latest: dict[str, SenseAddition] = {}
    for row in read_jsonl(SenseAddition, path):
        latest.pop(row.key, None)
        latest[row.key] = row
    return [row for row in latest.values() if row.status == "accepted"]


def apply_sense_additions(
    tables: TaggedTables, rows: list[SenseAddition]
) -> tuple[int, int, int]:
    """Add the accepted links, and the lemmas they need, in place.

    A link the build already has only takes the row's form note. A created lemma
    takes its part of speech from the concept's lexfile.

    Args:
        tables: The transformed tables, after the member-form drops.
        rows: Accepted rows, typically from `load_sense_additions`.

    Returns:
        ``(senses added, lemmas created, stale)``.
    """
    concepts = {concept_key(c.id): c for c in tables.concepts}
    lemmas = {lemma.id for lemma in tables.lemmas}
    senses = {(s.lemma_id, concept_key(s.concept_id)): s for s in tables.senses}
    added = created = stale = 0
    for row in rows:
        if not row.add:
            continue
        concept = concepts.get(row.concept_key)
        if concept is None:
            stale += 1
            continue
        existing = senses.get((row.lemma_id, row.concept_key))
        if existing is not None:
            existing.form_note = row.form_note or existing.form_note
            continue
        if row.lemma_id not in lemmas:
            pos = _LEXFILE_POS.get((concept.lexfile or "").split(".")[0])
            lemma = Lemma(
                text=row.word,
                language=row.language,
                part_of_speech=pos,
                sources=[SOURCE_MANUAL],
            )
            if lemma.id != row.lemma_id:
                # The word does not hash to the row's lemma: it was mistyped.
                stale += 1
                continue
            tables.lemmas.append(lemma)
            tables.lemma_sources.append(SOURCE_MANUAL)
            lemmas.add(lemma.id)
            created += 1
        sense = Sense(
            lemma_id=row.lemma_id,
            concept_id=concept.id,
            form_note=row.form_note or None,
        )
        tables.senses.append(sense)
        tables.sense_sources.append(SOURCE_MANUAL)
        senses[row.lemma_id, row.concept_key] = sense
        added += 1
    lg.info(
        "Sense additions: {} sense(s) added, {} lemma(s) created, {} stale",
        added,
        created,
        stale,
    )
    return added, created, stale
