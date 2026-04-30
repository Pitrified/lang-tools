"""Deterministic ID for a (text, language) pair.

Used as `Word.id` so the same word ingested from multiple sources collapses to
the same identifier. SHA-1 truncated to 16 hex chars (~64 bits) is plenty for
collision avoidance within a per-language dictionary.
"""

from __future__ import annotations

import hashlib

from lang_tools.language.normalization import normalize


def word_id(text: str, language: str) -> str:
    """Return a deterministic 16-char ID for ``(text, language)``.

    The text is normalized (accent-stripped, lowercased) before hashing so that
    different casings of the same word collapse to the same ID. Languages
    differ in how they treat ligatures, but this helper is intentionally
    language-agnostic to avoid a circular import on the `Language` model.

    Args:
        text: Word text in any case (accents preserved or not).
        language: ISO 639-1 code.

    Returns:
        16-character lowercase hex string.

    Example:
        ::

            word_id("A\u00e7\u00e3o", "pt")  # -> "..." (16 hex chars)
    """
    key = f"{language.lower()}::{normalize(text)}"
    return hashlib.sha1(key.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]
