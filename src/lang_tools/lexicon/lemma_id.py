"""Deterministic ID for a (text, language) pair.

Used as `Lemma.id` so the same lemma ingested from multiple sources collapses to
the same identifier. SHA-1 truncated to 16 hex chars (~64 bits) is plenty for
collision avoidance within a per-language dictionary.

Identity keeps case and accents (phase 8 step 9): pt ``avó`` / ``avô``, es
``ordenar`` / ``ordeñar`` and en ``Be`` (beryllium) / ``be`` are different words,
so they are different lemmas. Only Unicode composition and surrounding whitespace
are normalized. Search stays accent- and case-insensitive through
`Lemma.normalized`, which is not the identity. Capitalization noise (pt
``Cuspir`` for ``cuspir``) is folded by the build before ids are minted, not here.
"""

from __future__ import annotations

import hashlib
import unicodedata


def lemma_id(text: str, language: str) -> str:
    """Return a deterministic 16-char ID for ``(text, language)``.

    The text is NFC-normalized and stripped, but case and accents are kept, so
    two forms that differ only by an accent or by case are two lemmas. A
    lowercase, unaccented form hashes exactly as it did before identity became
    case- and accent-aware, so its id did not change.

    Args:
        text: Lemma text, exactly as displayed.
        language: ISO 639-1 code.

    Returns:
        16-character lowercase hex string.

    Example:
        ::

            lemma_id("avó", "pt") != lemma_id("avô", "pt")  # True
    """
    key = f"{language.lower()}::{unicodedata.normalize('NFC', text).strip()}"
    return hashlib.sha1(key.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]
