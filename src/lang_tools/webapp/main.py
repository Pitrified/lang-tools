"""FastAPI application factory for lang_tools."""

from fastapi import FastAPI
from fastapi_tools import create_app

from lang_tools.params.lang_tools_params import get_lang_tools_paths
from lang_tools.params.lang_tools_params import get_webapp_params
from lang_tools.webapp.routers.pages_router import router as pages_router


def build_app() -> FastAPI:
    """Build the FastAPI application using fastapi-tools.

    Returns:
        Configured FastAPI application instance.
    """
    params = get_webapp_params()
    config = params.to_config()
    paths = get_lang_tools_paths()

    return create_app(
        config=config,
        extra_routers=[pages_router],
        static_dir=paths.static_fol,
        templates_dir=paths.templates_fol,
    )
