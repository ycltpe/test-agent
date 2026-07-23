"""FastAPI routers for the agent service."""

from fastapi import APIRouter, Depends, HTTPException, status

from my_agent.agent.core import Agent
from my_agent.agent.models import AgentRequest, AgentResponse, HealthResponse
from my_agent.config import settings

router = APIRouter()


def get_agent() -> Agent:
    """Dependency that provides an Agent instance."""
    return Agent()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(version=settings.__dict__.get("version", "0.1.0"))


@router.post("/chat", response_model=AgentResponse)
async def chat(request: AgentRequest, agent: Agent = Depends(get_agent)) -> AgentResponse:
    """Send a message to the agent and receive a reply."""
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic API key is not configured.",
        )
    reply = await agent.run(request.message, session_id=request.session_id)
    return AgentResponse(reply=reply, session_id=request.session_id)


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str, agent: Agent = Depends(get_agent)) -> dict[str, str]:
    """Clear the conversation history for a session."""
    agent.clear_history(session_id)
    return {"status": "cleared", "session_id": session_id}
