"""Public lemma read API.

JSON endpoints exposing the frozen lemma query helpers
(`lang_tools.lexicon.lemma_store`) over HTTP. These are the network form of the
in-process read surface `lang-tutor` consumed in phase 2; the content contract
(the `Lemma` model) is unchanged - only the transport differs.

The content is public, so the endpoints require no authentication.

Routes:
    GET /api/v1/lemmas             - list lemmas, filtered by language and/or topic.
    GET /api/v1/lemmas/{lemma_id}  - fetch a single lemma by its deterministic id.
"""

from typing import Annotated

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma_store import get_lemma_by_id
from lang_tools.lexicon.lemma_store import get_lemmas_filtered

router = APIRouter(prefix="/api/v1/lemmas", tags=["lemmas"])


@router.get("", summary="List lemmas")
async def list_lemmas(
    language: Annotated[
        str | None,
        Query(description="ISO 639-1 language code"),
    ] = None,
    topic: Annotated[
        str | None,
        Query(description="Topic tag to filter by"),
    ] = None,
) -> list[Lemma]:
    """Return lemmas filtered by optional ``language`` and/or ``topic``.

    Args:
        language: ISO 639-1 code to filter by. No filter when None.
        topic: Topic tag to filter by. No filter when None.

    Returns:
        The matching lemmas (the full pool when no filter is given).
    """
    return get_lemmas_filtered(language=language, topic=topic)


@router.get("/{lemma_id}", summary="Fetch a lemma by id")
async def read_lemma(lemma_id: str) -> Lemma:
    """Return a single lemma by its deterministic id.

    Args:
        lemma_id: The deterministic id derived from ``(text, language)``.

    Returns:
        The matching lemma.

    Raises:
        HTTPException: 404 when no lemma has the given id.
    """
    lemma = get_lemma_by_id(lemma_id)
    if lemma is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lemma not found: {lemma_id}",
        )
    return lemma
