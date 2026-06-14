"""Application instance for uvicorn.

Entry point: uvicorn lang_tools.webapp.app:app
"""

from lang_tools.webapp.main import build_app

# Create application instance
app = build_app()

if __name__ == "__main__":
    import uvicorn

    from lang_tools.params.lang_tools_params import get_webapp_params

    params = get_webapp_params()
    uvicorn.run(
        "lang_tools.webapp.app:app",
        host=params.host,
        port=params.port,
        reload=params.debug,
    )
