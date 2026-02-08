import os

import pytest
import yaml
from httpx import ASGITransport, AsyncClient
from server import app


@pytest.mark.asyncio
async def test_get_models_config():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/models/config")
    assert response.status_code == 200
    config = response.json()
    assert "google" in config


@pytest.mark.asyncio
async def test_update_models_config():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Update google/heavy to a dummy value
        response = await ac.post(
            "/models/config",
            json={"provider": "google", "tier": "heavy", "model": "dummy-heavy-model"},
        )
    assert response.status_code == 200
    config = response.json()["config"]
    assert config["google"]["heavy"] == "dummy-heavy-model"


@pytest.mark.asyncio
async def test_update_agent_model():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.patch(
            "/agents/ResearchAgent/model",
            json={"model_provider": "openai", "model_tier": "heavy"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["model_provider"] == "openai"
    assert data["config"]["model_tier"] == "heavy"
