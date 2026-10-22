"""Lemma merging and deduplication.

Two lemmas with the same `(text, language)` (and therefore the same `Lemma.id`)
should collapse to one record whose metadata is the union of both. Richer
metadata wins where the two records disagree on a scalar field.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lang_tools.lexicon.lemma import Lemma

if TYPE_CHECKING:
    from collections.abc import Iterable


def _merge_lists(left: list, right: list) -> list:
    seen: list = []
    for item in (*left, *right):
        if item not in seen:
            seen.append(item)
    return seen


def merge_lemmas(left: Lemma, right: Lemma) -> Lemma:
    """Return a new `Lemma` that combines fields from `left` and `right`.

    The scalar ``part_of_speech`` prefers non-null over null; if both differ,
    ``left`` wins. Collection fields (``topics``, ``examples``, ``sources``)
    are merged. Lemma identity keeps case and accents, so two records with one
    id share their spelling (up to Unicode composition) and `left`'s is kept.

    Args:
        left: First record (its `text` is preserved).
        right: Second record.

    Returns:
        A new merged `Lemma` instance. `left` and `right` are not mutated.

    Raises:
        ValueError: If the two records have different IDs.
    """
    if left.id != right.id:
        msg = f"Cannot merge lemmas with different IDs: {left.id} vs {right.id}"
        raise ValueError(msg)

    return Lemma(
        text=left.text,
        language=left.language,
        normalized=left.normalized or right.normalized,
        part_of_speech=left.part_of_speech or right.part_of_speech,
        topics=_merge_lists(left.topics, right.topics),
        examples=_merge_lists(left.examples, right.examples),
        sources=_merge_lists(left.sources, right.sources),
    )


def deduplicate(lemmas: Iterable[Lemma]) -> list[Lemma]:
    """Collapse an iterable of `Lemma`s by ID, merging duplicates.

    Args:
        lemmas: Iterable of lemmas; may contain duplicates by ID.

    Returns:
        Insertion-ordered list of distinct `Lemma` records.
    """
    out: dict[str, Lemma] = {}
    for lemma in lemmas:
        if lemma.id in out:
            out[lemma.id] = merge_lemmas(out[lemma.id], lemma)
        else:
            out[lemma.id] = lemma
    return list(out.values())
