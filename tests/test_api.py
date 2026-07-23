"""Tests for the agent API endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient


@patch("my_agent.api.routes.settings")
def test_health(mock_settings, client: TestClient) -> None:
    mock_settings.__dict__ = {"version": "0.1.0"}
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@patch("my_agent.api.routes.settings")
@patch("my_agent.api.routes.Agent.run", new_callable=AsyncMock)
def test_chat(mock_run, mock_settings, client: TestClient) -> None:
    mock_settings.anthropic_api_key = "test-key"
    mock_run.return_value = "Hello, human."

    response = client.post("/api/v1/chat", json={"message": "hi", "session_id": "s1"})

    assert response.status_code == 200
    assert response.json() == {"reply": "Hello, human.", "session_id": "s1"}
    mock_run.assert_awaited_once_with("hi", session_id="s1")


@patch("my_agent.api.routes.settings")
def test_chat_missing_api_key(mock_settings, client: TestClient) -> None:
    mock_settings.anthropic_api_key = None
    response = client.post("/api/v1/chat", json={"message": "hi"})
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_clear_session(client: TestClient) -> None:
    response = client.delete("/api/v1/sessions/s1")
    assert response.status_code == 200
    assert response.json()["session_id"] == "s1"
