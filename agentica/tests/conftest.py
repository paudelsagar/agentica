from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from server import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture
async def async_client():
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
def mock_llm_response():
    """
    Fixture to create a mock LLM response.
    """

    def _create_response(content="Test response", tool_calls=None):
        mock_msg = MagicMock()
        mock_msg.content = content
        mock_msg.tool_calls = tool_calls or []
        return mock_msg

    return _create_response
