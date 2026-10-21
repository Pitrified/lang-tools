"""Decoupled relation edge tables.

Relations between lexical entities are stored as standalone edges rather than
embedded on the entities they connect, so each relationship lives in exactly
one place and never drifts when one side is updated.

`FalseFriendRelation` is a symmetric lemma-to-lemma edge (a misleading cognate
pair). Symmetric edges are stored in a canonical orientation
(``lemma_id_a < lemma_id_b``) so each pair appears once and dedups naturally.

`ConceptRelation` is a typed concept-to-concept edge (hypernymy, meronymy,
...), completed in phase 7. Directional relation types keep their source/target
order; symmetric types reuse the canonical-ordering trick.

`SenseRelation` is a typed sense-to-sense edge (phase 7). Antonymy lives here
because WordNet states it between word *senses*: collapsing it to lemmas would
claim `light` is the opposite of `heavy` in its illumination sense, and phase 2's
"lemma-level" note was wrong on exactly that point. The English sense pairs are
also derived up to concept-level `antonym` edges, which is how the languages
whose wordnets carry no sense relations get opposites at all.

Type vocabulary (phase 7): every stored type is in `CONCEPT_RELATION_TYPES` or
`SENSE_RELATION_TYPES`. The models do not reject other labels (tests and future
sources may use their own); the quality gate does, so an unreviewed type that
reaches the corpus fails the build check rather than a constructor.
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_validator

#: Directional, from the specific concept (``a``) to the broader one (``b``).
#: Hyponymy is the same edge read backwards, so it is never *stored* separately,
#: though the reader takes links stated from either side (phase 7).
RELATION_HYPERNYM = "hypernym"

#: Symmetric opposition. Stored sense-level (`SenseRelation`, English only) and
#: derived to concept level (`ConceptRelation`, provenance ``derived``).
RELATION_ANTONYM = "antonym"

#: Directional `ConceptRelation` types and what ``a -> b`` means for each. Each is
#: the one stored direction of a WordNet inverse pair (or has no inverse):
#:
#: - ``hypernym``: a is a kind of b (dog -> animal).
#: - ``instance_hypernym``: a is an instance of b (Rome -> national capital).
#:   Stored apart from ``hypernym`` (an instance is not a kind), but depth walks
#:   both - see `TAXONOMY_RELATIONS`.
#: - ``mero_member`` / ``mero_part`` / ``mero_substance``: b is a member / part /
#:   substance of a (car -> accelerator).
#: - ``entails``: doing a entails doing b (buy -> pay).
#: - ``causes``: a causes b (kill -> die).
DIRECTIONAL_CONCEPT_RELATIONS: frozenset[str] = frozenset(
    {
        RELATION_HYPERNYM,
        "instance_hypernym",
        "mero_member",
        "mero_part",
        "mero_substance",
        "entails",
        "causes",
    },
)

#: The directional types hypernym depth walks (phase 7 Decision 4, revisited).
#: ``wn``'s ``Synset.hypernyms()`` returns instance links too, so until phase 7
#: they were stored as ``hypernym`` and phase 6's depth - and the CEFR cutoffs
#: fitted on it - counted them. Walking both keeps that: Rome sits one level below
#: "national capital" instead of becoming a depth-0 root the score reads as
#: maximally general.
TAXONOMY_RELATIONS: frozenset[str] = frozenset({RELATION_HYPERNYM, "instance_hypernym"})

#: `ConceptRelation.relation_type` values whose endpoints are interchangeable.
#: These get canonical ``a < b`` ordering; every other type is directional and
#: keeps its source/target order. ``similar`` links satellite adjectives to their
#: head, ``also`` is WordNet's "see also", and ``attribute`` joins a noun to the
#: adjectives that value it (temperature - hot).
SYMMETRIC_CONCEPT_RELATIONS: frozenset[str] = frozenset(
    {"similar", "also", "attribute", RELATION_ANTONYM},
)

#: Every `ConceptRelation.relation_type` the build may store (the gate allowlist).
CONCEPT_RELATION_TYPES: frozenset[str] = (
    DIRECTIONAL_CONCEPT_RELATIONS | SYMMETRIC_CONCEPT_RELATIONS
)

#: `SenseRelation.relation_type` values whose endpoints are interchangeable.
SYMMETRIC_SENSE_RELATIONS: frozenset[str] = frozenset({RELATION_ANTONYM})

#: Every `SenseRelation.relation_type` the build may store (the gate allowlist).
#: ``derivation`` / ``pertainym`` are deferred: English-only morphology, no consumer.
SENSE_RELATION_TYPES: frozenset[str] = SYMMETRIC_SENSE_RELATIONS


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
    """A typed edge between two concepts.

    Attributes:
        concept_id_a: Source endpoint (or canonical-first when symmetric).
        concept_id_b: Target endpoint (or canonical-second when symmetric).
        relation_type: Relation label, e.g. ``"hypernym"`` or ``"mero_part"``
            (directional, see `DIRECTIONAL_CONCEPT_RELATIONS` for what each
            orientation means) or ``"similar"`` (symmetric, see
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


class SenseRelation(BaseModel):
    """A typed edge between two senses (lemma-in-a-concept), e.g. antonymy.

    The endpoints are `Sense.id` values, so the edge names *which meaning* of each
    word it relates. Symmetric types (`SYMMETRIC_SENSE_RELATIONS`) are stored in
    canonical ``a < b`` order, like `FalseFriendRelation`.

    Attributes:
        sense_id_a: First endpoint (canonical-first when symmetric).
        sense_id_b: Second endpoint.
        relation_type: Relation label, e.g. ``"antonym"``.
    """

    sense_id_a: str
    sense_id_b: str
    relation_type: str

    @model_validator(mode="after")
    def _canonical_order(self) -> SenseRelation:
        """Canonically order endpoints for symmetric relation types only."""
        if self.sense_id_a == self.sense_id_b:
            raise SelfRelationError(self.sense_id_a)
        if (
            self.relation_type in SYMMETRIC_SENSE_RELATIONS
            and self.sense_id_a > self.sense_id_b
        ):
            self.sense_id_a, self.sense_id_b = self.sense_id_b, self.sense_id_a
        return self
