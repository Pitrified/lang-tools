"""Deterministic ID for a `Sense` (the lemma <-> concept edge).

A sense is identified by its two endpoints. Because ``lemma_id`` and
``concept_id`` live in distinct namespaces, the pair has a fixed orientation
(lemma first, concept second) and needs no canonical reordering. SHA-1
truncated to 16 hex chars matches `lemma_id`'s collision budget.
"""

from __future__ import annotations

import hashlib


def sense_id(lemma_id: str, concept_id: str) -> str:
    """Return a deterministic 16-char id for the ``(lemma_id, concept_id)`` edge.

    Args:
        lemma_id: The lemma endpoint id.
        concept_id: The concept endpoint id.

    Returns:
        16-character lowercase hex string identifying the sense edge.

    Example:
        ::

            sense_id("0a1b2c3d4e5f6071", "c__bank-river__0011aabbccdd")
    """
    key = f"{lemma_id}::{concept_id}"
    return hashlib.sha1(key.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]
