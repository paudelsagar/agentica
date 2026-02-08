from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from server import app


@pytest.fixture
def client():
    return TestClient(app)


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
