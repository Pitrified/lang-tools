"""Static word-list ingestion (worldly-words style).

Accepts a list of dicts with at minimum ``text`` and ``language`` keys, plus
optional ``normalized``. Extra fields are ignored.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lang_tools.words.word import Word

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Iterator


def load_static_list(entries: Iterable[dict]) -> Iterator[Word]:
    """Yield `Word` objects from a minimal list of dicts.

    Args:
        entries: Iterable of dicts. Each dict must contain ``text`` and
            ``language``; ``normalized`` is filled in automatically when absent.

    Yields:
        `Word` instances tagged with ``sources=["static_list"]``.
    """
    for entry in entries:
        yield Word(
            text=entry["text"],
            language=entry["language"],
            normalized=entry.get("normalized", ""),
            sources=["static_list"],
        )
