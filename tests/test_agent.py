"""Tests for the agent core."""

from unittest.mock import AsyncMock, patch

import pytest

from my_agent.agent.core import Agent


@pytest.fixture
def agent():
    """Provide an Agent instance with a fake API key."""
    return Agent(api_key="test-key", model="test-model")


@pytest.mark.asyncio
async def test_run_stores_history(agent: Agent) -> None:
    fake_response = AsyncMock()
    fake_response.content = [type("Block", (), {"type": "text", "text": "reply"})]

    with patch.object(agent._client.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = fake_response
        reply = await agent.run("hello", session_id="s1")

    assert reply == "reply"
    assert len(agent.get_history("s1")) == 2
    assert agent.get_history("s1")[0]["role"] == "user"


@pytest.mark.asyncio
async def test_run_without_session_skips_history(agent: Agent) -> None:
    fake_response = AsyncMock()
    fake_response.content = [type("Block", (), {"type": "text", "text": "reply"})]

    with patch.object(agent._client.messages, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = fake_response
        reply = await agent.run("hello")

    assert reply == "reply"
    assert agent.get_history("s1") == []


def test_clear_history(agent: Agent) -> None:
    agent._history["s1"] = []
    agent.clear_history("s1")
    assert "s1" not in agent._history
