"""Decoupled relation edge tables.

Relations between lexical entities are stored as standalone edges rather than
embedded on the entities they connect, so each relationship lives in exactly
one place and never drifts when one side is updated.

`FalseFriendRelation` is a symmetric lemma-to-lemma edge (a misleading cognate
pair). Symmetric edges are stored in a canonical orientation
(``lemma_id_a < lemma_id_b``) so each pair appears once and dedups naturally.

`ConceptRelation` is a typed concept-to-concept edge (hypernymy, meronymy,
...), populated in phase 7. Directional relation types keep their source/target
order; symmetric types reuse the canonical-ordering trick. Antonymy is a
lemma-level relation and will arrive as a future sibling of
`FalseFriendRelation`, not here.
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

#: The one `ConceptRelation.relation_type` the initial build emits (5.5 Step 4):
#: directional, from the specific concept (``a``) to the broader one (``b``).
#: Hyponymy is the same edge read backwards, so it is never stored separately.
RELATION_HYPERNYM = "hypernym"

#: `ConceptRelation.relation_type` values whose endpoints are interchangeable.
#: These get canonical ``a < b`` ordering; every other type is directional and
#: keeps its source/target order.
SYMMETRIC_CONCEPT_RELATIONS: frozenset[str] = frozenset({"related"})


class SelfRelationError(ValueError):
    """Raised when a relation edge connects an entity to itself."""

    def __init__(self, entity_id: str) -> None:
        """Initialize with the repeated endpoint id.

        Args:
            entity_id: The id that appeared on both ends of the edge.
        """
        super().__init__(
            f"A relation cannot connect an entity to itself: {entity_id!r}",
        )
        self.entity_id = entity_id


class FalseFriendRelation(BaseModel):
    """A symmetric false-friend (misleading cognate) edge between two lemmas.

    Attributes:
        lemma_id_a: First lemma endpoint; held ``< lemma_id_b`` canonically.
        lemma_id_b: Second lemma endpoint.
        similarity_score: Optional 0.0-1.0 visual / phonetic similarity.
        explanation_notes: Per-language notes on the trap, keyed by ISO 639-1
            code.
    """

    lemma_id_a: str
    lemma_id_b: str
    similarity_score: float | None = None
    explanation_notes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _canonical_order(self) -> FalseFriendRelation:
        """Enforce ``lemma_id_a < lemma_id_b`` so the pair is stored once."""
        if self.lemma_id_a == self.lemma_id_b:
            raise SelfRelationError(self.lemma_id_a)
        if self.lemma_id_a > self.lemma_id_b:
            self.lemma_id_a, self.lemma_id_b = self.lemma_id_b, self.lemma_id_a
        return self


class ConceptRelation(BaseModel):
    """A typed edge between two concepts (stub; populated in phase 7).

    Attributes:
        concept_id_a: Source endpoint (or canonical-first when symmetric).
        concept_id_b: Target endpoint (or canonical-second when symmetric).
        relation_type: Relation label, e.g. ``"hypernym"`` (directional),
            ``"meronym"`` (directional), or ``"related"`` (symmetric, see
            `SYMMETRIC_CONCEPT_RELATIONS`).
    """

    concept_id_a: str
    concept_id_b: str
    relation_type: str

    @model_validator(mode="after")
    def _canonical_order(self) -> ConceptRelation:
        """Canonically order endpoints for symmetric relation types only."""
        if self.concept_id_a == self.concept_id_b:
            raise SelfRelationError(self.concept_id_a)
        if (
            self.relation_type in SYMMETRIC_CONCEPT_RELATIONS
            and self.concept_id_a > self.concept_id_b
        ):
            self.concept_id_a, self.concept_id_b = self.concept_id_b, self.concept_id_a
        return self
