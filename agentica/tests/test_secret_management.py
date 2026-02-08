import os

import pytest
from httpx import ASGITransport, AsyncClient
from server import app


@pytest.mark.asyncio
async def test_get_secrets_status():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/config/secrets")
    assert response.status_code == 200
    status = response.json()
    assert "GOOGLE_API_KEY" in status
    assert "OPENAI_API_KEY" in status
    assert status["GOOGLE_API_KEY"]["set"] is True
    # Verify masking
    val = status["GOOGLE_API_KEY"]["value"]
    assert "..." in val


@pytest.mark.asyncio
async def test_update_secrets():
    dummy_key = "sk-test-runtime-key-12345"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Update secret
        response = await ac.post("/config/secrets", json={"OPENAI_API_KEY": dummy_key})
        assert response.status_code == 200
        assert response.json() == {"status": "updated", "keys": ["OPENAI_API_KEY"]}

        # 2. Verify masked status
        response = await ac.get("/config/secrets")
        assert response.status_code == 200
        status = response.json()
        assert status["OPENAI_API_KEY"]["set"] is True
        assert status["OPENAI_API_KEY"]["value"].startswith("sk-t")
        assert status["OPENAI_API_KEY"]["value"].endswith("45")
