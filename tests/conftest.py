"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from my_agent.main import create_app


@pytest.fixture
def app():
    """Provide the FastAPI app instance."""
    return create_app()


@pytest.fixture
def client(app):
    """Provide a synchronous test client."""
    return TestClient(app)
