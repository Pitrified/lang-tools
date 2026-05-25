"""Exercise API endpoints.

JSON API for exercise interactions (start, submit, finish).
Called by the exercise page JavaScript.
"""

from __future__ import annotations

import random
from typing import Annotated
from typing import Any
from typing import Literal

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi_tools.schemas.auth import SessionData  # noqa: TC002
from pydantic import BaseModel
from pydantic import Field

from lang_tools.exercises.diacritic_typing import DiacriticTypingExercise
from lang_tools.exercises.pair_matching import PairMatchingExercise
from lang_tools.exercises.sentence_reconstruction import SentenceReconstructionExercise
from lang_tools.exercises.wordle import WordleExercise
from lang_tools.webapp.core.auth import get_current_user
from lang_tools.words.word_store import get_words_filtered

router = APIRouter(prefix="/exercises", tags=["exercises-api"])

# In-memory session state (per-user game state).
# In production this would be stored in a DB or cache.
_active_rounds: dict[str, Any] = {}


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
    hint_level: Literal["off", "show_unaccented", "show_all"] = "off"


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
    """Start a new pair matching round using real words."""
    words = get_words_filtered(language=body.language)
    # Filter to words that have the target translation
    words_with_trans = [
        w for w in words if body.target_language in w.translations
    ]
    if len(words_with_trans) < body.num_words:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough words with {body.target_language} translation.",
        )
    selected = random.sample(words_with_trans, body.num_words)
    exercise = PairMatchingExercise(target_language=body.target_language)
    round_ = exercise.start(selected)

    # Store round for submit calls
    round_key = f"{user.user_id}:pair_matching"
    _active_rounds[round_key] = (exercise, round_)

    return ExerciseResponse(
        status="ok",
        data={
            "left_words": round_.prompt["left_words"],
            "right_words": round_.prompt["right_words"],
        },
    )


class PairMatchingSubmitRequest(BaseModel):
    """Request body to submit a pair match."""

    left: str
    right: str


@router.post("/pair-matching/submit")
async def pair_matching_submit(
    body: PairMatchingSubmitRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Submit a single pair match."""
    round_key = f"{user.user_id}:pair_matching"
    state = _active_rounds.get(round_key)
    if not state:
        raise HTTPException(status_code=400, detail="No active pair matching game.")
    exercise, round_ = state
    result = exercise.submit(round_, (body.left, body.right))
    return ExerciseResponse(
        status="ok",
        data={"correct": result.correct, "left": body.left, "right": body.right},
    )


@router.post("/wordle/start")
async def wordle_start(
    body: WordleStartRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Start a new wordle game with a real word."""
    words = get_words_filtered(language=body.language)
    candidates = [w for w in words if w.length == body.word_length]
    if not candidates:
        raise HTTPException(
            status_code=400,
            detail=f"No {body.word_length}-letter words for {body.language}.",
        )
    target = random.choice(candidates)
    exercise = WordleExercise()
    round_ = exercise.start(target)

    round_key = f"{user.user_id}:wordle"
    _active_rounds[round_key] = (exercise, round_)

    return ExerciseResponse(
        status="ok",
        data={
            "word_length": round_.prompt["word_length"],
            "max_attempts": round_.prompt["max_attempts"],
        },
    )


@router.post("/wordle/guess")
async def wordle_guess(
    body: WordleGuessRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Submit a wordle guess."""
    round_key = f"{user.user_id}:wordle"
    state = _active_rounds.get(round_key)
    if not state:
        raise HTTPException(status_code=400, detail="No active wordle game.")
    exercise, round_ = state
    result = exercise.submit(round_, body.guess)
    guesses = round_.prompt["guesses"]
    results = round_.prompt["results"]
    max_attempts: int = round_.prompt["max_attempts"]
    finished = result.correct or len(guesses) >= max_attempts
    data: dict[str, Any] = {
        "letters": results[-1] if results else [],
        "finished": finished,
        "correct": result.correct,
        "attempts_left": max_attempts - len(guesses),
        "keyboard_state": round_.prompt["keyboard_state"],
    }
    if finished:
        data["answer"] = round_.expected.target.text
        del _active_rounds[round_key]
    return ExerciseResponse(status="ok", data=data)


@router.post("/diacritic-typing/start")
async def diacritic_start(
    body: DiacriticStartRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Start a new diacritic typing round with a real accented word."""
    words = get_words_filtered(language=body.language)
    accented = [w for w in words if w.has_accent]
    if not accented:
        raise HTTPException(
            status_code=400,
            detail=f"No accented words for {body.language}.",
        )
    word = random.choice(accented)
    exercise = DiacriticTypingExercise()
    round_ = exercise.start(word, hint_level=body.hint_level)

    round_key = f"{user.user_id}:diacritic"
    _active_rounds[round_key] = (exercise, round_)

    return ExerciseResponse(
        status="ok",
        data={
            "display": round_.prompt["display"],
            "glosses": round_.prompt["glosses"],
            "word_length": len(round_.prompt["display"]),
            "translation": word.translations.get("en", ""),
        },
    )


@router.post("/diacritic-typing/keystroke")
async def diacritic_keystroke(
    body: DiacriticKeystrokeRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Submit a keystroke for diacritic typing."""
    round_key = f"{user.user_id}:diacritic"
    state = _active_rounds.get(round_key)
    if not state:
        raise HTTPException(
            status_code=400, detail="No active diacritic game.",
        )
    exercise, round_ = state
    result = exercise.submit(round_, body.character)
    data: dict[str, Any] = {
        "display": round_.prompt["display"],
        "correct_so_far": result.correct,
        "finished": len(result.word_results) > 0,
        "errors": round_.expected.error_count,
    }
    if len(result.word_results) > 0:
        del _active_rounds[round_key]
    return ExerciseResponse(status="ok", data=data)


@router.post("/sentence-reconstruction/start")
async def reconstruction_start(
    body: ReconstructionStartRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Start a sentence reconstruction round using word examples."""
    words = get_words_filtered(language=body.language)
    words_with_examples = [w for w in words if w.examples]
    if not words_with_examples:
        raise HTTPException(
            status_code=400,
            detail=f"No words with examples for {body.language}.",
        )
    word = random.choice(words_with_examples)
    example = word.examples[0]
    exercise = SentenceReconstructionExercise()
    round_ = exercise.start(
        sentence=example.sentence,
        translation=example.translation or word.translations.get("en", ""),
    )

    round_key = f"{user.user_id}:reconstruction"
    _active_rounds[round_key] = (exercise, round_)

    return ExerciseResponse(
        status="ok",
        data={
            "translation": round_.prompt["translation"],
            "portions": round_.prompt["portions"],
        },
    )


@router.post("/sentence-reconstruction/submit")
async def reconstruction_submit(
    body: ReconstructionSubmitRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Submit a reconstruction attempt."""
    round_key = f"{user.user_id}:reconstruction"
    state = _active_rounds.get(round_key)
    if not state:
        raise HTTPException(
            status_code=400, detail="No active reconstruction game.",
        )
    exercise, round_ = state
    result = exercise.submit(round_, body.selected_portions)
    data: dict[str, Any] = {
        "correct": result.correct,
        "finished": len(result.word_results) > 0,
    }
    if len(result.word_results) > 0:
        data["answer"] = " ".join(round_.expected)
        del _active_rounds[round_key]
    return ExerciseResponse(status="ok", data=data)


@router.post("/conversational-tutor/message")
async def tutor_message(
    body: TutorMessageRequest,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> ExerciseResponse:
    """Send a message to the conversational tutor.

    Note: Requires LLM integration. Returns placeholder for now.
    """
    return ExerciseResponse(
        status="ok",
        data={
            "reply": (
                "Conversational tutor requires LLM integration. "
                "This endpoint will be connected when llm-core chains "
                "are wired up."
            ),
            "correction": None,
        },
    )

