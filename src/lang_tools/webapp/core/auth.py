"""Authentication dependencies with dev-mode bypass.

In dev mode (``ENV_STAGE_TYPE=dev``), Google OAuth is disabled entirely.
A hardcoded dev user is injected so the app starts with zero configuration.
In prod mode, the standard fastapi-tools OAuth flow is used.
"""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import Annotated

from fastapi import Cookie
from fastapi import Depends
from fastapi import Request
from fastapi_tools.exceptions import NotAuthenticatedException
from fastapi_tools.schemas.auth import SessionData

from lang_tools.params.env_type import EnvStageType

_DEV_USER = SessionData(
    session_id="dev-session",
    user_id="dev-user",
    email="dev@localhost",
    name="Dev User",
    picture=None,
    created_at=datetime(2024, 1, 1, tzinfo=UTC),
    expires_at=datetime(2099, 12, 31, tzinfo=UTC),
)


def _is_dev_mode() -> bool:
    """Check if the app is running in dev stage."""
    return EnvStageType.from_env_var() == EnvStageType.DEV


async def _get_session_from_cookie(
    request: Request,
    session: Annotated[str | None, Cookie(alias="session")] = None,
) -> SessionData | None:
    """Extract session from cookie via the app's session store."""
    if not session:
        return None
    session_store = request.app.state.session_store
    return session_store.get_session(session)


async def get_current_user(
    request: Request,
    session_data: Annotated[SessionData | None, Depends(_get_session_from_cookie)],
) -> SessionData:
    """Get the current authenticated user.

    In dev mode, returns a hardcoded dev user without requiring OAuth.
    In prod mode, requires a valid session cookie.

    Args:
        request: The incoming request.
        session_data: Session data from cookie (prod mode).

    Returns:
        Authenticated session data.
    """
    if _is_dev_mode():
        return _DEV_USER
    if session_data is None:
        raise NotAuthenticatedException
    return session_data


async def get_optional_user(
    request: Request,
    session_data: Annotated[SessionData | None, Depends(_get_session_from_cookie)],
) -> SessionData | None:
    """Get the current user if authenticated, or the dev user in dev mode.

    Args:
        request: The incoming request.
        session_data: Session data from cookie (prod mode).

    Returns:
        Session data or None (prod unauthenticated).
    """
    if _is_dev_mode():
        return _DEV_USER
    return session_data


GetCurrentUser = Annotated[SessionData, Depends(get_current_user)]
GetOptionalUser = Annotated[SessionData | None, Depends(get_optional_user)]

