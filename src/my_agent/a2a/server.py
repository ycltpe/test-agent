"""构建符合 A2A 协议的 FastAPI 应用。"""

from a2a.server.request_handlers.default_request_handler_v2 import (
    DefaultRequestHandlerV2,
)
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentProvider,
    AgentSkill,
)
from fastapi import FastAPI

from my_agent import __version__
from my_agent.a2a.executor import A2AAgentExecutor
from my_agent.config import settings


def build_agent_card(host: str | None = None, port: int | None = None) -> AgentCard:
    """构建描述本服务的 A2A AgentCard。"""
    host = host or settings.host
    port = port or settings.port
    return AgentCard(
        name="my-agent",
        description="一个基于 FastAPI + LLM 的 A2A 协议 Agent 服务",
        version=__version__,
        provider=AgentProvider(organization="my-agent"),
        supported_interfaces=[
            AgentInterface(
                url=f"http://{host}:{port}/a2a",
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        capabilities=AgentCapabilities(streaming=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="chat",
                name="多轮对话",
                description="通用对话能力，支持基于 context_id 的多轮会话",
                tags=["chat"],
                examples=["你好", "帮我总结一下 A2A 协议"],
            )
        ],
    )


def create_a2a_app(
    executor: A2AAgentExecutor | None = None,
    card: AgentCard | None = None,
    rpc_url: str = "/a2a",
) -> FastAPI:
    """创建只承载 A2A 端点的 FastAPI 应用。"""
    card = card or build_agent_card()
    request_handler = DefaultRequestHandlerV2(
        agent_executor=executor or A2AAgentExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=card,
    )
    app = FastAPI(title="my-agent A2A", version=__version__)
    add_a2a_routes_to_fastapi(
        app,
        agent_card_routes=create_agent_card_routes(card),
        jsonrpc_routes=create_jsonrpc_routes(request_handler, rpc_url=rpc_url),
    )
    return app
