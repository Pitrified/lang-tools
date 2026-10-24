"""The `Sense` model: the explicit lemma <-> concept edge.

`Sense` is the **canonical membership record** - the single place the
lemma-to-concept relationship is stored. It also hosts the per-sense signals
that must not live on the token: frequency and CEFR complexity. The "bank"
polysemy trap is the rationale: the river-bank sense and the money-bank sense
of one lemma differ wildly in frequency and difficulty, so those values belong
on the sense, not on `Lemma`.

The per-sense values (`token_frequency`, `sense_frequency`, `cefr_level`) are
defined now and left empty; they are populated in phase 6. Convenience
navigation (`sense.lemma -> Lemma`, `sense.concept -> Concept`) is a
representation-layer concern hydrated by the store in phase 4, not a persisted
field, so it is intentionally absent here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel
from pydantic import Field
from pydantic import computed_field

from lang_tools.lexicon.hydration import SenseNotHydratedError
from lang_tools.lexicon.hydration import require
from lang_tools.lexicon.sense_id import sense_id

if TYPE_CHECKING:
    from lang_tools.lexicon.concept import Concept
    from lang_tools.lexicon.lemma import Lemma


class Sense(BaseModel):
    """One meaning of one lemma: the edge from a `Lemma` to a `Concept`.

    Attributes:
        lemma_id: Id of the lemma endpoint.
        concept_id: Id of the concept endpoint.
        token_frequency: Corpus frequency of the lemma's surface form, shared
            across its senses. Populated in phase 6.
        sense_frequency: Frequency of *this* meaning specifically. Populated in
            phase 6.
        frequency_is_estimated: True when the frequency values are estimated
            rather than measured.
        cefr_level: CEFR complexity band of this sense (``"A1"`` ... ``"C2"``).
            Populated in phase 6.
        cefr_is_estimated: True when `cefr_level` is estimated rather than taken
            from a graded list.
        lemma: Resolved lemma endpoint. Store-hydrated, never persisted
            (``exclude=True``); ``None`` until hydration. Read via
            `resolve_lemma` to fail loud when unhydrated.
        concept: Resolved concept endpoint. Same hydration contract as `lemma`.
    """

    lemma_id: str
    concept_id: str
    token_frequency: float | None = None
    sense_frequency: float | None = None
    frequency_is_estimated: bool = False
    cefr_level: str | None = None
    cefr_is_estimated: bool = False

    # Representation-layer back-references; populated by the store at hydration,
    # excluded from serialization so the persisted shape stays thin and stable.
    lemma: Lemma | None = Field(default=None, exclude=True, repr=False)
    concept: Concept | None = Field(default=None, exclude=True, repr=False)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def id(self) -> str:
        """Deterministic id derived from ``(lemma_id, concept_id)``."""
        return sense_id(self.lemma_id, self.concept_id)

    def resolve_lemma(self) -> Lemma:
        """Return the hydrated lemma endpoint.

        Returns:
            The `Lemma` this sense points at.

        Raises:
            SenseNotHydratedError: If the store has not hydrated `lemma`.
        """
        return require(self.lemma, "Sense", "lemma", error=SenseNotHydratedError)

    def resolve_concept(self) -> Concept:
        """Return the hydrated concept endpoint.

        Returns:
            The `Concept` this sense points at.

        Raises:
            SenseNotHydratedError: If the store has not hydrated `concept`.
        """
        return require(self.concept, "Sense", "concept", error=SenseNotHydratedError)
