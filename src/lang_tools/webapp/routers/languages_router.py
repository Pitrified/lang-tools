"""Language configuration page routes.

Serves pages for viewing available languages and their settings.
"""

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi_tools.schemas.auth import SessionData

from lang_tools.language.language import LANGUAGE_PRESETS
from lang_tools.language.language import get_language
from lang_tools.webapp.core.auth import get_current_user

router = APIRouter(prefix="/languages", tags=["languages"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def language_list(
    request: Request,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render available languages page.

    Args:
        request: Incoming request.
        user: Authenticated user session.

    Returns:
        Language list page HTML.
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/languages/index.html",
        {
            "user": user,
            "active_page": "languages",
            "languages": LANGUAGE_PRESETS,
        },
    )


@router.get("/{code}", response_class=HTMLResponse, include_in_schema=False)
async def language_detail(
    request: Request,
    code: str,
    user: Annotated[SessionData, Depends(get_current_user)],
) -> HTMLResponse:
    """Render single language detail page.

    Args:
        request: Incoming request.
        code: ISO 639-1 language code.
        user: Authenticated user session.

    Returns:
        Language detail page HTML.
    """
    language = get_language(code)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "pages/languages/detail.html",
        {
            "user": user,
            "active_page": "languages",
            "language": language,
        },
    )
