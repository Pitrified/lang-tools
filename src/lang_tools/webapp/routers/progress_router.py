"""Progress and stats page routes.

Serves pages for viewing user learning progress and statistics.
"""

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi_tools.schemas.auth import SessionData

from lang_tools.webapp.core.auth import get_current_user

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def progress_dashboard(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render overall progress dashboard.

    Args:
        request: Incoming request.
        user: Authenticated user session.

    Returns:
        Progress dashboard page HTML.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/progress/index.html",
        {"user": user, "active_page": "progress"},
    )


@router.get("/{language}", response_class=HTMLResponse, include_in_schema=False)
async def progress_by_language(
    request: Request,
    language: str,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render per-language progress breakdown.

    Args:
        request: Incoming request.
        language: ISO 639-1 language code.
        user: Authenticated user session.

    Returns:
        Language-specific progress page HTML.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/progress/language.html",
        {
            "user": user,
            "active_page": "progress",
            "language_code": language,
        },
    )
