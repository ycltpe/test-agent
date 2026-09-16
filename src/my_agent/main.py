"""FastAPI application entry point."""

import uvicorn
from fastapi import FastAPI

from a2a.server.routes.agent_card_routes import create_agent_card_routes

from my_agent import __version__
from my_agent.a2a.server import build_agent_card, create_a2a_app
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
    card = build_agent_card()
    # A2A 协议端点：JSON-RPC 入口挂载在 /a2a，AgentCard 按规范暴露在根路径
    app.mount("/a2a", create_a2a_app(card=card, rpc_url="/"))
    for route in create_agent_card_routes(card):
        app.routes.append(route)
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


def main_a2a() -> None:
    """只运行 A2A 协议的独立服务。"""
    uvicorn.run(
        "my_agent.a2a.server:create_a2a_app",
        factory=True,
        host=settings.host,
        port=settings.a2a_port,
    )


if __name__ == "__main__":
    main()
