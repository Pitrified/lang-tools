"""Deterministic ID for a (text, language) pair.

Used as `Lemma.id` so the same lemma ingested from multiple sources collapses to
the same identifier. SHA-1 truncated to 16 hex chars (~64 bits) is plenty for
collision avoidance within a per-language dictionary.
"""

from __future__ import annotations

import hashlib

from lang_tools.language.normalization import normalize


def lemma_id(text: str, language: str) -> str:
    """Return a deterministic 16-char ID for ``(text, language)``.

    The text is normalized (accent-stripped, lowercased) before hashing so that
    different casings of the same lemma collapse to the same ID. Languages
    differ in how they treat ligatures, but this helper is intentionally
    language-agnostic to avoid a circular import on the `Language` model.

    Args:
        text: Lemma text in any case (accents preserved or not).
        language: ISO 639-1 code.

    Returns:
        16-character lowercase hex string.

    Example:
        ::

            lemma_id("Ação", "pt")  # -> "..." (16 hex chars)
    """
    key = f"{language.lower()}::{normalize(text)}"
    return hashlib.sha1(key.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]
