"""Public concept and relation read API.

JSON endpoints exposing the concept-graph read surface
(`lang_tools.lexicon.lemma_store`) over HTTP. These are kept separate from the
lemma endpoints so the lemma payload stays lean: the heavier concept graph and
relation edges are fetched only when a caller needs them (e.g. building a
vocabulary-trap exercise), not bundled into every lemma response.

The content is public, so the endpoints require no authentication.

Routes:
    GET /api/v1/concepts/{concept_id}            - fetch a concept by id.
    GET /api/v1/concepts/{concept_id}/relations  - typed concept-to-concept edges.
"""

from typing import Annotated

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from lang_tools.lexicon.concept import Concept
from lang_tools.lexicon.lemma_store import concept_relations_for
from lang_tools.lexicon.lemma_store import get_concept_by_id
from lang_tools.lexicon.relations import ConceptRelation

router = APIRouter(prefix="/api/v1/concepts", tags=["concepts"])


@router.get("/{concept_id}", summary="Fetch a concept by id")
async def read_concept(concept_id: str) -> Concept:
    """Return a single concept by its id.

    Args:
        concept_id: The ``c__{slug}__{hash}`` concept id.

    Returns:
        The matching concept (id + per-language definitions).

    Raises:
        HTTPException: 404 when no concept has the given id.
    """
    concept = get_concept_by_id(concept_id)
    if concept is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Concept not found: {concept_id}",
        )
    return concept


@router.get("/{concept_id}/relations", summary="List a concept's relations")
async def list_concept_relations(
    concept_id: str,
    relation_type: Annotated[
        str | None,
        Query(description="Restrict to a single relation type, e.g. 'hypernym'"),
    ] = None,
) -> list[ConceptRelation]:
    """Return the typed concept-to-concept edges touching a concept.

    Args:
        concept_id: The concept whose relations to fetch.
        relation_type: Optional relation-type filter.

    Returns:
        The matching relation edges (empty when none).
    """
    return concept_relations_for(concept_id, relation_type=relation_type)
