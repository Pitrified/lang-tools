"""Exercise API endpoints.

JSON API for exercise interactions (start, submit, finish).
Called by the exercise page JavaScript.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Annotated
from typing import Any

from fastapi import APIRouter
from fastapi import Depends
from pydantic import BaseModel
from pydantic import Field

from lang_tools.webapp.core.auth import get_current_user

if TYPE_CHECKING:
    from fastapi_tools.schemas.auth import SessionData

router = APIRouter(prefix="/api/v1/exercises", tags=["exercises-api"])


class PairMatchingStartRequest(BaseModel):
    """Request body to start a pair matching round."""

    language: str = "pt"
    target_language: str = "en"
    num_words: int = 5


class WordleStartRequest(BaseModel):
    """Request body to start a wordle game."""

    language: str = "pt"
    word_length: int = 5


class WordleGuessRequest(BaseModel):
    """Request body to submit a wordle guess."""

    guess: str


class DiacriticStartRequest(BaseModel):
    """Request body to start a diacritic typing round."""

    language: str = "pt"
    hint_level: str = "off"


class DiacriticKeystrokeRequest(BaseModel):
    """Request body to submit a keystroke."""

    character: str


class ReconstructionStartRequest(BaseModel):
    """Request body to start a sentence reconstruction round."""

    language: str = "pt"


class ReconstructionSubmitRequest(BaseModel):
    """Request body to submit a portion selection."""

    selected_portions: list[str]


class TutorMessageRequest(BaseModel):
    """Request body to send a tutor message."""

    text: str
    topic: str = ""


class ExerciseResponse(BaseModel):
    """Generic exercise response."""

    status: str = "ok"
    data: dict[str, Any] = Field(default_factory=dict)


@router.post("/pair-matching/start")
async def pair_matching_start(
    body: PairMatchingStartRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Start a new pair matching round.

    Args:
        body: Request with language settings.
        user: Authenticated user.

    Returns:
        Round prompt data with left and right word columns.
    """
    # Placeholder - in full implementation, selects words from DB
    return ExerciseResponse(
        status="ok",
        data={
            "message": "Pair matching not yet connected to word store.",
            "left_words": [],
            "right_words": [],
        },
    )


@router.post("/wordle/start")
async def wordle_start(
    body: WordleStartRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Start a new wordle game.

    Args:
        body: Request with language and word length.
        user: Authenticated user.

    Returns:
        Game configuration (word length, max attempts).
    """
    max_attempts = body.word_length + 1
    return ExerciseResponse(
        status="ok",
        data={
            "word_length": body.word_length,
            "max_attempts": max_attempts,
            "message": "Wordle not yet connected to word store.",
        },
    )


@router.post("/wordle/guess")
async def wordle_guess(
    body: WordleGuessRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Submit a wordle guess.

    Args:
        body: Request with the guess.
        user: Authenticated user.

    Returns:
        Letter results for the guess.
    """
    return ExerciseResponse(
        status="ok",
        data={"message": "Wordle guess evaluation not yet implemented."},
    )


@router.post("/diacritic-typing/start")
async def diacritic_start(
    body: DiacriticStartRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Start a new diacritic typing round.

    Args:
        body: Request with language and hint level.
        user: Authenticated user.

    Returns:
        Word display and keyboard configuration.
    """
    return ExerciseResponse(
        status="ok",
        data={"message": "Diacritic typing not yet connected to word store."},
    )


@router.post("/diacritic-typing/keystroke")
async def diacritic_keystroke(
    body: DiacriticKeystrokeRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Submit a keystroke for diacritic typing.

    Args:
        body: Request with the typed character.
        user: Authenticated user.

    Returns:
        Updated display state.
    """
    return ExerciseResponse(
        status="ok",
        data={"message": "Diacritic keystroke evaluation not yet implemented."},
    )


@router.post("/sentence-reconstruction/start")
async def reconstruction_start(
    body: ReconstructionStartRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Start a sentence reconstruction round.

    Args:
        body: Request with target language.
        user: Authenticated user.

    Returns:
        Translation and shuffled portions.
    """
    return ExerciseResponse(
        status="ok",
        data={"message": "Sentence reconstruction not yet connected to content."},
    )


@router.post("/sentence-reconstruction/submit")
async def reconstruction_submit(
    body: ReconstructionSubmitRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Submit a reconstruction attempt.

    Args:
        body: Request with selected portions in order.
        user: Authenticated user.

    Returns:
        Whether the reconstruction is correct.
    """
    return ExerciseResponse(
        status="ok",
        data={"message": "Reconstruction evaluation not yet implemented."},
    )


@router.post("/conversational-tutor/message")
async def tutor_message(
    body: TutorMessageRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Send a message to the conversational tutor.

    Args:
        body: Request with user text and topic.
        user: Authenticated user.

    Returns:
        Tutor response with correction and continuation.
    """
    return ExerciseResponse(
        status="ok",
        data={"message": "Conversational tutor not yet connected to LLM."},
    )
