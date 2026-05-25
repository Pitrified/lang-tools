"""Exercise page routes.

Serves Jinja2 templates for each exercise type: pair-matching, wordle,
diacritic-typing, sentence-reconstruction, and conversational-tutor.
"""

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi_tools.schemas.auth import SessionData

from lang_tools.exercises.base import EXERCISE_TYPES
from lang_tools.webapp.core.auth import get_current_user

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def exercise_list(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render exercise selection page.

    Args:
        request: Incoming request.
        user: Authenticated user session.

    Returns:
        Exercise list page HTML.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/exercises/index.html",
        {
            "user": user,
            "active_page": "exercises",
            "exercise_types": EXERCISE_TYPES,
        },
    )


@router.get(
    "/pair-matching",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def pair_matching_page(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render pair matching exercise page.

    Args:
        request: Incoming request.
        user: Authenticated user session.

    Returns:
        Pair matching exercise page HTML.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/exercises/pair_matching.html",
        {"user": user, "active_page": "exercises"},
    )


@router.get("/wordle", response_class=HTMLResponse, include_in_schema=False)
async def wordle_page(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render wordle exercise page.

    Args:
        request: Incoming request.
        user: Authenticated user session.

    Returns:
        Wordle exercise page HTML.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/exercises/wordle.html",
        {"user": user, "active_page": "exercises"},
    )


@router.get(
    "/diacritic-typing",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def diacritic_typing_page(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render diacritic typing exercise page.

    Args:
        request: Incoming request.
        user: Authenticated user session.

    Returns:
        Diacritic typing exercise page HTML.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/exercises/diacritic_typing.html",
        {"user": user, "active_page": "exercises"},
    )


@router.get(
    "/sentence-reconstruction",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def sentence_reconstruction_page(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render sentence reconstruction exercise page.

    Args:
        request: Incoming request.
        user: Authenticated user session.

    Returns:
        Sentence reconstruction exercise page HTML.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/exercises/sentence_reconstruction.html",
        {"user": user, "active_page": "exercises"},
    )


@router.get(
    "/conversational-tutor",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def conversational_tutor_page(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render conversational tutor exercise page.

    Args:
        request: Incoming request.
        user: Authenticated user session.

    Returns:
        Conversational tutor exercise page HTML.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/exercises/conversational_tutor.html",
        {"user": user, "active_page": "exercises"},
    )
