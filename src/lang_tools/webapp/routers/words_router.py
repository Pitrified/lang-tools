"""Public word read API.

JSON endpoints exposing the frozen word query helpers
(`lang_tools.words.word_store`) over HTTP. These are the network form of the
in-process read surface `lang-tutor` consumed in phase 2; the content contract
(the `Word` model) is unchanged - only the transport differs.

The content is public, so the endpoints require no authentication.

Routes:
    GET /api/v1/words            - list words, filtered by language and/or topic.
    GET /api/v1/words/{word_id}  - fetch a single word by its deterministic id.
"""

from typing import Annotated

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query
from fastapi import status

from lang_tools.words.word import Word
from lang_tools.words.word_store import get_word_by_id
from lang_tools.words.word_store import get_words_filtered

router = APIRouter(prefix="/api/v1/words", tags=["words"])


@router.get("", summary="List words")
async def list_words(
    language: Annotated[
        str | None,
        Query(description="ISO 639-1 language code"),
    ] = None,
    topic: Annotated[
        str | None,
        Query(description="Topic tag to filter by"),
    ] = None,
) -> list[Word]:
    """Return words filtered by optional ``language`` and/or ``topic``.

    Args:
        language: ISO 639-1 code to filter by. No filter when None.
        topic: Topic tag to filter by. No filter when None.

    Returns:
        The matching words (the full pool when no filter is given).
    """
    return get_words_filtered(language=language, topic=topic)


@router.get("/{word_id}", summary="Fetch a word by id")
async def read_word(word_id: str) -> Word:
    """Return a single word by its deterministic id.

    Args:
        word_id: The deterministic id derived from ``(text, language)``.

    Returns:
        The matching word.

    Raises:
        HTTPException: 404 when no word has the given id.
    """
    word = get_word_by_id(word_id)
    if word is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Word not found: {word_id}",
        )
    return word
