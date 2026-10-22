"""Public drill-card read API.

JSON endpoints over the `LemmaCard` drill view
(`lang_tools.lexicon.lemma_store.lemma_cards`): a lemma joined with its best
sense's CEFR band, gloss, translations, and example sentences. This is the
surface ``lang-tutor`` builds exercise rounds from - one bounded call per round
instead of pulling a whole language and joining the graph client-side.

The content is public, so the endpoints require no authentication.

Routes:
    GET /api/v1/cards              - a bounded, filtered sample of cards (the
        query string is a `CardQuery`; list fields repeat the key, e.g.
        ``translation_languages=en&translation_languages=it``).
    GET /api/v1/cards/{lemma_id}   - the card of one lemma.
    GET /api/v1/cards/{lemma_id}/senses - one card per sense, best first.
"""

from typing import Annotated

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from lang_tools.lexicon.card import CardQuery
from lang_tools.lexicon.card import LemmaCard
from lang_tools.lexicon.lemma_store import lemma_card
from lang_tools.lexicon.lemma_store import lemma_cards
from lang_tools.lexicon.lemma_store import lemma_sense_cards

router = APIRouter(prefix="/api/v1/cards", tags=["cards"])


@router.get("", summary="Sample drill cards")
async def list_cards(query: Annotated[CardQuery, Query()]) -> list[LemmaCard]:
    """Return up to ``query.limit`` cards matching the filters.

    Args:
        query: The `CardQuery`, read from the query string.

    Returns:
        The matching cards (random order unless ``order=frequency``).
    """
    return lemma_cards(query)


@router.get("/{lemma_id}", summary="Fetch one lemma's drill card")
async def read_card(
    lemma_id: str,
    gloss_language: Annotated[
        str,
        Query(description="Language of the card's gloss"),
    ] = "en",
    translation_languages: Annotated[
        list[str] | None,
        Query(description="Languages to list translations in (repeatable)"),
    ] = None,
) -> LemmaCard:
    """Return the drill card of one lemma.

    Args:
        lemma_id: The lemma's deterministic id.
        gloss_language: Language of the card's gloss.
        translation_languages: Languages to fill the translations with
            (``["en"]`` when omitted).

    Returns:
        The lemma's card.

    Raises:
        HTTPException: 404 when no lemma has the given id.
    """
    card = lemma_card(
        lemma_id,
        gloss_language=gloss_language,
        translation_languages=translation_languages or ["en"],
    )
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Lemma not found: {lemma_id}",
        )
    return card


@router.get("/{lemma_id}/senses", summary="List one card per sense of a lemma")
async def read_sense_cards(
    lemma_id: str,
    gloss_language: Annotated[
        str,
        Query(description="Language of each card's gloss"),
    ] = "en",
    translation_languages: Annotated[
        list[str] | None,
        Query(description="Languages to list translations in (repeatable)"),
    ] = None,
) -> list[LemmaCard]:
    """Return one card per sense of a lemma, best sense first.

    Args:
        lemma_id: The lemma's deterministic id.
        gloss_language: Language of each card's gloss.
        translation_languages: Languages to fill the translations with
            (``["en"]`` when omitted).

    Returns:
        The cards (empty for an unknown lemma or one with no sense).
    """
    return lemma_sense_cards(
        lemma_id,
        gloss_language=gloss_language,
        translation_languages=translation_languages or ["en"],
    )
