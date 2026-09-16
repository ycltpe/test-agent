"""Agent core logic."""

from collections.abc import Sequence

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from my_agent.config import settings


class Agent:
    """A thin wrapper around an LLM that maintains per-session history."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._client = AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key,
            base_url=base_url or settings.anthropic_base_url,
        )
        self._model = model or settings.default_model
        self._history: dict[str, list[MessageParam]] = {}

    def get_history(self, session_id: str | None) -> list[MessageParam]:
        """Return the conversation history for a session."""
        if session_id is None:
            return []
        return self._history.get(session_id, [])

    def _update_history(
        self, session_id: str | None, user_message: str, assistant_message: str
    ) -> None:
        if session_id is None:
            return
        history = self._history.setdefault(session_id, [])
        history.append(MessageParam(role="user", content=user_message))
        history.append(MessageParam(role="assistant", content=assistant_message))

    async def run(self, message: str, session_id: str | None = None) -> str:
        """Send a message to the model and return the reply."""
        messages: Sequence[MessageParam] = [
            *self.get_history(session_id),
            MessageParam(role="user", content=message),
        ]
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=messages,
        )
        reply = "".join(block.text for block in response.content if block.type == "text")
        self._update_history(session_id, message, reply)
        return reply

    def clear_history(self, session_id: str | None) -> None:
        """Clear the conversation history for a session."""
        if session_id is not None and session_id in self._history:
            del self._history[session_id]
