"""FastAPI application entry point."""

import uvicorn
from fastapi import FastAPI

from my_agent import __version__
from my_agent.api.routes import router
from my_agent.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
    )
    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()


def main() -> None:
    """Run the application with uvicorn."""
    uvicorn.run(
        "my_agent.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    main()
