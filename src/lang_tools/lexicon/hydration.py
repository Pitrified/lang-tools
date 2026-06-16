"""Errors for the representation-layer hydration of lexical models.

The persisted models (`Lemma`, `Concept`, `Sense`) are thin and id-only; the
store populates their serialization-excluded back-reference fields (`senses`,
`concepts`, `lemma`, ...) once at load time. An object that was built ad hoc -
in ingestion before the registries exist, or in a unit test - is **not**
hydrated: its back-ref fields are ``None``. Accessing such a field through the
``resolve_*`` guards raises a clear error rather than returning ``None``
silently, so a "you forgot to load the store" bug surfaces instead of hiding.
The persisted id fields (``lemma_id`` / ``concept_id``) stay the always-present
fallback.
"""

from __future__ import annotations


class NotHydratedError(RuntimeError):
    """Raised when a store-populated back-reference is read before hydration."""

    def __init__(self, owner: str, attr: str) -> None:
        """Initialize with the model and attribute that were not hydrated.

        Args:
            owner: Name of the model class whose field is unhydrated.
            attr: Name of the back-reference attribute that is ``None``.
        """
        super().__init__(
            f"{owner}.{attr} is not hydrated; load it through the store "
            f"(LexiconStore) before reading back-references.",
        )
        self.owner = owner
        self.attr = attr


class SenseNotHydratedError(NotHydratedError):
    """Raised when a `Sense` endpoint (`lemma` / `concept`) is read unhydrated."""


def require[T](
    value: T | None,
    owner: str,
    attr: str,
    *,
    error: type[NotHydratedError] = NotHydratedError,
) -> T:
    """Return a hydrated back-reference, failing loud when it is ``None``.

    Args:
        value: The back-reference field value.
        owner: Name of the owning model class (for the message).
        attr: Name of the attribute being read (for the message).
        error: Concrete `NotHydratedError` subclass to raise.

    Returns:
        `value`, guaranteed non-``None``.

    Raises:
        NotHydratedError: When `value` is ``None`` (the store did not hydrate it).
    """
    if value is None:
        raise error(owner, attr)
    return value
