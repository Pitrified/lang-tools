"""Word browsing page routes.

Serves pages for browsing and viewing vocabulary words.
"""

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi_tools.schemas.auth import SessionData

from lang_tools.webapp.core.auth import get_current_user
from lang_tools.words.word_store import get_word_by_id
from lang_tools.words.word_store import get_words_filtered

router = APIRouter(prefix="/words", tags=["words"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def word_list(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
    language: Annotated[str | None, Query()] = None,
    topic: Annotated[str | None, Query()] = None,
) -> HTMLResponse:
    """Render word browsing page with optional filters."""
    words = get_words_filtered(language=language, topic=topic)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/words/index.html",
        {
            "user": user,
            "active_page": "words",
            "language_filter": language,
            "topic_filter": topic,
            "words": words,
        },
    )


@router.get("/partial", response_class=HTMLResponse, include_in_schema=False)
async def word_list_partial(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
    language: Annotated[str | None, Query()] = None,
    topic: Annotated[str | None, Query()] = None,
) -> HTMLResponse:
    """Return only the word table partial (for HTMX filter updates)."""
    words = get_words_filtered(language=language, topic=topic)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/words/_word_table.html",
        {"words": words},
    )


@router.get("/{word_id}", response_class=HTMLResponse, include_in_schema=False)
async def word_detail(
    request: Request,
    word_id: str,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render word detail page."""
    word = get_word_by_id(word_id)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/words/detail.html",
        {
            "user": user,
            "active_page": "words",
            "word_id": word_id,
            "word": word,
        },
    )
