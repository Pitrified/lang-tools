"""Deterministic ID for a `Concept` (language-independent synset).

A concept id is ``c__{slug}__{hash[:12]}``: a human-readable slug for
legibility plus a 12-hex safety net hashed from the stable source key (the OMW
synset / ILI key). The hash - not the slug - guarantees uniqueness, so editing
a slug for readability never changes the id and two concepts that happen to
derive the same slug still get distinct ids.

The slug is supplied pre-computed (the slug-source choice - OMW/ILI key first,
else English gloss - is finalized in the ingestion phase), mirroring
`lemma_id`'s language-agnostic, side-effect-free style.
"""

from __future__ import annotations

import hashlib
import re

#: Shape of a valid concept id: ``c__{slug}__{12 hex}``. The slug is any
#: non-empty run of lowercase letters, digits, and hyphens.
CONCEPT_ID_RE = re.compile(r"^c__[a-z0-9-]+__[0-9a-f]{12}$")


class EmptyConceptSlugError(ValueError):
    """Raised when `concept_id` is given an empty or blank slug."""

    def __init__(self) -> None:
        """Initialize with a fixed, descriptive message."""
        super().__init__("Concept slug must be a non-empty string.")


def concept_id(slug: str, source_key: str) -> str:
    """Return a deterministic ``c__{slug}__{hash[:12]}`` id for a concept.

    Args:
        slug: Pre-computed human-readable slug (lowercase, hyphenated). Used
            only for legibility; it does not feed the hash.
        source_key: Stable upstream key (OMW synset / ILI id) hashed into the
            12-hex suffix so regeneration is deterministic and slug edits do
            not change the id.

    Returns:
        The concept id string.

    Raises:
        EmptyConceptSlugError: If `slug` is empty or blank.

    Example:
        ::

            # -> "c__library-building__<12 hex>"
            concept_id("library-building", "omw-en-03660909-n")
    """
    slug = slug.strip()
    if not slug:
        raise EmptyConceptSlugError
    digest = hashlib.sha1(source_key.encode("utf-8"), usedforsecurity=False).hexdigest()
    return f"c__{slug}__{digest[:12]}"
