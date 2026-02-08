import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.core.model_router import ModelRouter


# Helper to mock aiosqlite 'async with db.execute(...) as cursor'
class MockAsyncContextManager:
    def __init__(self, return_value):
        self.return_value = return_value

    async def __aenter__(self):
        return self.return_value

    async def __aexit__(self, exc_type, exc, tb):
        pass


@pytest.mark.asyncio
async def test_get_optimal_tier_default():
    router = ModelRouter()
    # Test with non-existent DB
    with patch("os.path.exists", return_value=False):
        tier = await router.get_optimal_tier("TestAgent")
        assert tier == "fast"


@pytest.mark.asyncio
async def test_get_optimal_tier_promotes_on_latency():
    router = ModelRouter()

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.side_effect = [(20000,), (5, 5)]  # Latency then success

    # Use MagicMock for execute so it returns the context manager immediately
    mock_db = MagicMock()
    mock_db.execute.side_effect = [
        MockAsyncContextManager(mock_cursor),
        MockAsyncContextManager(mock_cursor),
    ]

    with patch("os.path.exists", return_value=True):
        with patch("aiosqlite.connect", return_value=MockAsyncContextManager(mock_db)):
            tier = await router.get_optimal_tier("ResearchAgent", provider="google")
            assert tier == "heavy"


@pytest.mark.asyncio
async def test_get_optimal_tier_promotes_on_failure():
    router = ModelRouter()

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.side_effect = [(2000,), (2, 5)]  # Latency then success (40%)

    mock_db = MagicMock()
    mock_db.execute.side_effect = [
        MockAsyncContextManager(mock_cursor),
        MockAsyncContextManager(mock_cursor),
    ]

    with patch("os.path.exists", return_value=True):
        with patch("aiosqlite.connect", return_value=MockAsyncContextManager(mock_db)):
            tier = await router.get_optimal_tier("CoderAgent", provider="google")
            assert tier == "heavy"


@pytest.mark.asyncio
async def test_get_optimal_tier_stays_fast():
    router = ModelRouter()

    mock_cursor = AsyncMock()
    mock_cursor.fetchone.side_effect = [(1000,), (5, 5)]  # Latency then success

    mock_db = MagicMock()
    mock_db.execute.side_effect = [
        MockAsyncContextManager(mock_cursor),
        MockAsyncContextManager(mock_cursor),
    ]

    with patch("os.path.exists", return_value=True):
        with patch("aiosqlite.connect", return_value=MockAsyncContextManager(mock_db)):
            tier = await router.get_optimal_tier("DataAgent", provider="google")
            assert tier == "fast"
