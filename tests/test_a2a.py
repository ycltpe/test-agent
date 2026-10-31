"""A2A 协议端到端测试。

流程：通过 TestClient 直接访问挂载在 FastAPI 上的 A2A JSON-RPC 端点，
打桩 LangChain LLM 避免真实 API 调用。
"""

import uuid
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

import my_agent.a2a.executor as executor_module
from my_agent.main import create_app


@pytest.fixture
def mock_llm() -> Iterator[AsyncMock]:
    """打桩执行器模块里的 LLM，让回复带上对话历史长度，便于断言多轮上下文。"""

    async def fake_ainvoke(messages, **kwargs):
        # 历史消息条数（不含本次用户消息）
        history_len = len(messages) - 1
        return AIMessage(content=f"收到，历史消息数={history_len}")

    with patch.object(executor_module, "_llm") as mock:
        mock.ainvoke.side_effect = fake_ainvoke
        yield mock


@pytest.fixture
def a2a_client(mock_llm: AsyncMock) -> Iterator[TestClient]:
    """返回只承载 A2A 端点的测试客户端。"""
    from my_agent.a2a.server import create_a2a_app

    with TestClient(create_a2a_app()) as client:
        yield client


def send_message(client: TestClient, text: str, context_id: str | None = None) -> dict:
    """发送一条 A2A JSON-RPC 消息并返回 result。"""
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "SendMessage",
        "params": {
            "message": {
                "role": "ROLE_USER",
                "parts": [{"text": text}],
                "messageId": str(uuid.uuid4()),
            },
        },
    }
    if context_id:
        payload["params"]["message"]["contextId"] = context_id
    resp = client.post("/a2a", json=payload, headers={"A2A-Version": "1.0"})
    assert resp.status_code == 200
    body = resp.json()
    assert "result" in body, f"JSON-RPC 返回错误: {body}"
    return body["result"]


def test_agent_card(a2a_client: TestClient) -> None:
    """GET /.well-known/agent-card.json 返回 AgentCard。"""
    resp = a2a_client.get("/.well-known/agent-card.json")
    assert resp.status_code == 200
    card = resp.json()
    print(f"\ncard:{card}")
    assert card["name"] == "my-agent"
    assert card["supportedInterfaces"][0]["url"].endswith("/a2a")
    assert card["skills"], "AgentCard 应至少声明一个 skill"


def test_send_message_returns_completed_task(a2a_client: TestClient) -> None:
    """SendMessage 返回终态为 COMPLETED 的任务，且包含 agent 回复。"""
    result = send_message(a2a_client, "你好")
    task = result["task"]
    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    text = "".join(p.get("text", "") for p in task["status"]["message"]["parts"])
    assert "收到" in text
    # artifact 中也应携带回复内容
    artifact_text = "".join(
        p.get("text", "") for a in task.get("artifacts", []) for p in a.get("parts", [])
    )
    assert "收到" in artifact_text


def test_multi_turn_context_preserved(a2a_client: TestClient, mock_llm: AsyncMock) -> None:
    """同一 contextId 的第二、三轮请求应携带之前的会话历史。"""
    first = send_message(a2a_client, "第一轮")
    context_id = first["task"]["contextId"]

    second = send_message(a2a_client, "第二轮", context_id=context_id)
    history_text = "".join(
        p.get("text", "") for p in second["task"]["status"]["message"]["parts"]
    )
    # 第一轮 Q&A 共 2 条历史
    assert "历史消息数=2" in history_text

    third = send_message(a2a_client, "第三轮", context_id=context_id)
    history_text3 = "".join(
        p.get("text", "") for p in third["task"]["status"]["message"]["parts"]
    )
    assert "历史消息数=4" in history_text3


def test_get_task(a2a_client: TestClient) -> None:
    """GetTask 能取回已创建的任务。"""
    result = send_message(a2a_client, "查一下任务")
    task_id = result["task"]["id"]
    resp = a2a_client.post(
        "/a2a",
        json={
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "GetTask",
            "params": {"id": task_id},
        },
        headers={"A2A-Version": "1.0"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["id"] == task_id
    assert body["result"]["status"]["state"] == "TASK_STATE_COMPLETED"


def test_main_app_exposes_a2a(mock_llm: AsyncMock) -> None:
    """主应用同时暴露 /api/v1 与 /a2a 端点。"""
    app = create_app()
    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        card_resp = client.get("/.well-known/agent-card.json")
        assert card_resp.status_code == 200
        result = send_message(client, "主应用 A2A 测试")
        assert result["task"]["status"]["state"] == "TASK_STATE_COMPLETED"
