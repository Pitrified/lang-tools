"""Shared fixtures for content read API tests.

The app is built with ``create_app`` and a debug test config (matching the
fastapi-tools test pattern) so ``TestClient`` requests are not rejected by the
trusted-host middleware.
"""

from collections.abc import Generator

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi_tools import create_app
from fastapi_tools.config.webapp_config import CORSConfig
from fastapi_tools.config.webapp_config import GoogleOAuthConfig
from fastapi_tools.config.webapp_config import RateLimitConfig
from fastapi_tools.config.webapp_config import SessionConfig
from fastapi_tools.config.webapp_config import WebappConfig
import pytest

from lang_tools.webapp.routers.lemmas_router import router as lemmas_router


@pytest.fixture
def test_config() -> WebappConfig:
    """Create a debug webapp configuration for tests."""
    return WebappConfig(
        host="127.0.0.1",
        port=8000,
        debug=True,
        app_name="Lang Tools API",
        app_version="0.1.0-test",
        cors=CORSConfig(allow_origins=["http://localhost:3000"]),
        session=SessionConfig(
            secret_key="test_secret_key_for_testing_only_do_not_use_in_prod",  # noqa: S106 # pragma: allowlist secret
            max_age=3600,
        ),
        rate_limit=RateLimitConfig(requests_per_minute=100),
        google_oauth=GoogleOAuthConfig(
            client_id="test_client_id",
            client_secret="test_client_secret",  # noqa: S106 # pragma: allowlist secret
            redirect_uri="http://localhost:8000/auth/google/callback",
        ),
    )


@pytest.fixture
def app(test_config: WebappConfig) -> FastAPI:
    """Build the content read API application."""
    return create_app(config=test_config, extra_routers=[lemmas_router])


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient]:
    """Create a test client for the read API."""
    with TestClient(app) as test_client:
        yield test_client
