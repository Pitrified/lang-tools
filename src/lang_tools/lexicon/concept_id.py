"""Deterministic ID for a `Concept` (language-independent synset).

A concept id is ``c__{slug}__{hash[:12]}``: a human-readable slug for
legibility plus a 12-hex safety net hashed from the stable source key (the OMW
synset / ILI key). The hash - not the slug - guarantees uniqueness, so two
concepts that happen to derive the same slug still get distinct ids. A slug
change does change the id string, but never its hash half: `concept_key`
returns that half, and curated inputs that must survive a re-slug (phase 8)
match on it rather than on the full id.

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
    return f"c__{slug}__{source_key_hash(source_key)}"


def source_key_hash(source_key: str) -> str:
    """Return the 12-hex hash a concept id carries for `source_key`.

    It is what `concept_key` reads back out of an id, available before the slug
    (and so the id) is known - which is when slug assignment needs it.
    """
    digest = hashlib.sha1(source_key.encode("utf-8"), usedforsecurity=False)
    return digest.hexdigest()[:12]


class InvalidConceptIdForKeyError(ValueError):
    """Raised when `concept_key` is given a string that is not a concept id."""

    def __init__(self, value: str) -> None:
        """Initialize with the offending value.

        Args:
            value: The string that does not match `CONCEPT_ID_RE`.
        """
        super().__init__(f"Not a concept id: {value!r}")
        self.value = value


def concept_key(cid: str) -> str:
    """Return the slug-independent half of a concept id (its 12-hex hash).

    The hash is computed from the source grouping key alone, so it is the same
    before and after any slug change; the slug half is not.

    Args:
        cid: A concept id of the form ``c__{slug}__{hash}``.

    Returns:
        The 12-character hex suffix.

    Raises:
        InvalidConceptIdForKeyError: If `cid` is not a well-formed concept id.

    Example:
        ::

            concept_key("c__cut-noun-act__0011aabbccdd")  # -> "0011aabbccdd"
    """
    if not CONCEPT_ID_RE.match(cid):
        raise InvalidConceptIdForKeyError(cid)
    return cid.rsplit("__", 1)[1]
