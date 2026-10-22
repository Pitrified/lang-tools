"""Public lemma read API.

JSON endpoints exposing the frozen lemma query helpers
(`lang_tools.lexicon.lemma_store`) over HTTP. These are the network form of the
in-process read surface `lang-tutor` consumed in phase 2; the content contract
(the `Lemma` model) is unchanged - only the transport differs.

The content is public, so the endpoints require no authentication.

Routes:
    GET /api/v1/lemmas                            - one page of lemmas, filtered
        by language, topic and/or a search prefix (``q``); the total match
        count is in the ``X-Total-Count`` header.
    GET /api/v1/lemmas/{lemma_id}                 - fetch a single lemma by id.
    GET /api/v1/lemmas/{lemma_id}/false-friends   - the lemma's false-friend edges.
"""

from typing import Annotated

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import Response
from fastapi import status
from pydantic import BaseModel

from lang_tools.lexicon.lemma import Lemma
from lang_tools.lexicon.lemma_store import count_lemmas_filtered
from lang_tools.lexicon.lemma_store import get_false_friends_for_lemma
from lang_tools.lexicon.lemma_store import get_lemma_by_id
from lang_tools.lexicon.lemma_store import get_lemmas_filtered
from lang_tools.lexicon.relations import FalseFriendRelation

router = APIRouter(prefix="/api/v1/lemmas", tags=["lemmas"])

#: Default and maximum page size of the lemma list.
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 500


class FalseFriendHit(BaseModel):
    """One false-friend match: the other lemma plus the edge connecting it.

    Attributes:
        lemma: The misleading-cognate counterpart of the queried lemma.
        relation: The false-friend edge (similarity, learner notes).
    """

    lemma: Lemma
    relation: FalseFriendRelation


@router.get("", summary="List lemmas")
async def list_lemmas(
    response: Response,
    language: Annotated[
        str | None,
        Query(description="ISO 639-1 language code"),
    ] = None,
    topic: Annotated[
        str | None,
        Query(description="Topic tag to filter by"),
    ] = None,
    q: Annotated[
        str | None,
        Query(description="Prefix of the accent- and case-folded form"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description="Page size"),
    ] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0, description="Matches to skip")] = 0,
) -> list[Lemma]:
    """Return one page of lemmas filtered by language, topic and/or prefix.

    The list is paged because the full corpus holds hundreds of thousands of
    lemmas; pages are ordered by the folded form. The total number of matches
    is returned in the ``X-Total-Count`` header.

    Args:
        response: The response, to carry the total-count header.
        language: ISO 639-1 code to filter by. No filter when None.
        topic: Topic tag to filter by. No filter when None.
        q: Search prefix, folded like `Lemma.normalized`.
        limit: Page size.
        offset: Matches to skip before the page.

    Returns:
        The page of matching lemmas.
    """
    response.headers["X-Total-Count"] = str(
        count_lemmas_filtered(language=language, topic=topic, query=q),
    )
    return get_lemmas_filtered(
        language=language,
        topic=topic,
        query=q,
        limit=limit,
        offset=offset,
    )


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


@router.get("/{lemma_id}/false-friends", summary="List a lemma's false friends")
async def read_false_friends(lemma_id: str) -> list[FalseFriendHit]:
    """Return the false-friend matches of a lemma.

    Each match pairs the counterpart lemma with the edge that links them
    (similarity score and per-language learner notes). Fetched on demand so the
    plain lemma payload stays lean.

    Args:
        lemma_id: The deterministic id of the queried lemma.

    Returns:
        The false-friend hits (empty when the lemma has none).
    """
    return [
        FalseFriendHit(lemma=other, relation=edge)
        for other, edge in get_false_friends_for_lemma(lemma_id)
    ]
