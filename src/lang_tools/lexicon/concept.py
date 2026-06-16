"""The `Concept` model: a language-independent synset.

A `Concept` is the unit of meaning shared across languages. Lemmas point at it
through the explicit `Sense` edge (see `lang_tools.lexicon.sense`); the concept
itself stores only its id and its per-language canonical definitions. This is
the persisted shape - thin and drift-free.

Persistence note:
    The brainstorm's ``lemmas`` membership field is deliberately **not** stored
    here. With `Sense` as the explicit edge, per-language membership is fully
    derivable (group the concept's senses, bucket each by its lemma's
    language), so persisting it would duplicate the edge and risk one-sided
    drift. The convenient ``concept.lemmas`` grouping returns as a computed,
    store-hydrated view in the representation layer (phase 4), not as a stored
    field.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

from lang_tools.lexicon.concept_id import CONCEPT_ID_RE
from lang_tools.lexicon.hydration import require

if TYPE_CHECKING:
    from lang_tools.lexicon.lemma import Lemma
    from lang_tools.lexicon.sense import Sense


class InvalidConceptIdError(ValueError):
    """Raised when a `Concept` is built with an id that is not well-formed."""

    def __init__(self, value: str) -> None:
        """Initialize with the offending id value.

        Args:
            value: The id string that failed the ``c__{slug}__{hash}`` check.
        """
        super().__init__(
            f"Concept id is not well-formed (expected c__<slug>__<12 hex>): {value!r}",
        )
        self.value = value


class Concept(BaseModel):
    """A language-independent unit of meaning (a synset).

    Attributes:
        id: Deterministic id of the form ``c__{slug}__{hash[:12]}``, built at
            ingestion via `concept_id` from the stable OMW/ILI source key.
        definitions: Per-language canonical gloss, keyed by ISO 639-1 code
            (e.g. ``{"en": "...", "pt": "..."}``). The canonical home for
            glosses, which no longer live on `Lemma`.
        senses: Resolved `Sense` edges into this concept. Store-hydrated, never
            persisted (``exclude=True``); ``None`` until hydration. Read via
            `resolve_senses` to fail loud when unhydrated.
        lemmas: Per-language grouping of the lemmas that realise this concept,
            keyed by ISO 639-1 code. Derived from `senses` at hydration (never
            persisted), so it cannot drift from the sense table on disk. Read
            via `resolve_lemmas` to fail loud when unhydrated.
    """

    id: str
    definitions: dict[str, str] = Field(default_factory=dict)

    # Representation-layer back-references; see `Sense.lemma` for the contract.
    senses: list[Sense] | None = Field(default=None, exclude=True, repr=False)
    lemmas: dict[str, list[Lemma]] | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        """Reject ids that do not match the ``c__{slug}__{hash}`` shape."""
        if not CONCEPT_ID_RE.match(value):
            raise InvalidConceptIdError(value)
        return value

    def resolve_senses(self) -> list[Sense]:
        """Return the hydrated `Sense` edges into this concept.

        Returns:
            The senses linking lemmas to this concept (possibly empty).

        Raises:
            NotHydratedError: If the store has not hydrated `senses`.
        """
        return require(self.senses, "Concept", "senses")

    def resolve_lemmas(self) -> dict[str, list[Lemma]]:
        """Return the hydrated per-language lemma grouping.

        Returns:
            Mapping of language code to the lemmas realising this concept.

        Raises:
            NotHydratedError: If the store has not hydrated `lemmas`.
        """
        return require(self.lemmas, "Concept", "lemmas")
