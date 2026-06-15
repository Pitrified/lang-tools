"""FastAPI application factory for the lang-tools content read API.

`build_app()` assembles the public read service: the standard fastapi-tools
app (health, CORS, security headers, error handling) plus the lemma read router.
The service serves content the operator materialised by cloning with git-lfs;
see ``docs/guides/run_service.md`` for the operator setup.
"""

from fastapi import FastAPI
from fastapi_tools import create_app

from lang_tools.params.lang_tools_params import get_webapp_params
from lang_tools.webapp.routers.lemmas_router import router as lemmas_router


def build_app() -> FastAPI:
    """Build the FastAPI content read API using fastapi-tools.

    Returns:
        Configured FastAPI application instance serving the lemma read API.
    """
    config = get_webapp_params().to_config()

    return create_app(
        config=config,
        extra_routers=[lemmas_router],
    )
