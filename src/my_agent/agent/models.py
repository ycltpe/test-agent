"""Pydantic models for the agent API."""

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Incoming request payload for the agent endpoint."""

    message: str = Field(..., min_length=1, description="User message to the agent.")
    session_id: str | None = Field(
        default=None, description="Optional session identifier for continuity."
    )


class AgentResponse(BaseModel):
    """Outgoing response payload from the agent endpoint."""

    reply: str = Field(..., description="Agent's text reply.")
    session_id: str | None = Field(default=None, description="Session identifier.")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    version: str
