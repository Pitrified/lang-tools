"""Word merging and deduplication.

Two words with the same `(text, language)` (and therefore the same `Word.id`)
should collapse to one record whose metadata is the union of both. Richer
metadata wins where the two records disagree on a scalar field.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lang_tools.words.word import Word

if TYPE_CHECKING:
    from collections.abc import Iterable


def _merge_lists(left: list, right: list) -> list:
    seen: list = []
    for item in (*left, *right):
        if item not in seen:
            seen.append(item)
    return seen


def merge_words(left: Word, right: Word) -> Word:
    """Return a new `Word` that combines fields from `left` and `right`.

    Scalar fields (``part_of_speech``, ``frequency``) prefer non-null over
    null; if both differ, ``left`` wins. Collection fields (``translations``,
    ``topics``, ``glosses``, ``examples``, ``false_friends``, ``sources``) are
    merged. The resulting `text` keeps the `left` spelling so that accent
    information is preserved when one side has it and the other does not.

    Args:
        left: First record (its `text` is preserved).
        right: Second record.

    Returns:
        A new merged `Word` instance. `left` and `right` are not mutated.

    Raises:
        ValueError: If the two records have different IDs.
    """
    if left.id != right.id:
        msg = f"Cannot merge words with different IDs: {left.id} vs {right.id}"
        raise ValueError(msg)

    has_accent_left = any(c.isalpha() and not c.isascii() for c in left.text)
    text = left.text if has_accent_left else right.text
    if not text:
        text = left.text

    return Word(
        text=text,
        language=left.language,
        normalized=left.normalized or right.normalized,
        part_of_speech=left.part_of_speech or right.part_of_speech,
        frequency=left.frequency or right.frequency,
        translations={**right.translations, **left.translations},
        topics=_merge_lists(left.topics, right.topics),
        glosses=_merge_lists(left.glosses, right.glosses),
        examples=_merge_lists(left.examples, right.examples),
        false_friends=_merge_lists(left.false_friends, right.false_friends),
        sources=_merge_lists(left.sources, right.sources),
    )


def deduplicate(words: Iterable[Word]) -> list[Word]:
    """Collapse an iterable of `Word`s by ID, merging duplicates.

    Args:
        words: Iterable of words; may contain duplicates by ID.

    Returns:
        Insertion-ordered list of distinct `Word` records.
    """
    out: dict[str, Word] = {}
    for word in words:
        if word.id in out:
            out[word.id] = merge_words(out[word.id], word)
        else:
            out[word.id] = word
    return list(out.values())
