import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient
from server import app
from src.core.db_manager import db_manager


@pytest.mark.asyncio
async def test_db_init_and_agent_list():
    """Verifies that the database initializes and serves agents at startup."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Wait for startup event to finish (if not already)
        await asyncio.sleep(1)

        response = await ac.get("/agents")
        assert response.status_code == 200
        agents = response.json()
        assert "ResearchAgent" in agents
        assert agents["ResearchAgent"]["model_provider"] == "openai"


@pytest.mark.asyncio
async def test_agent_lifecycle_in_db():
    """Verifies creating, updating, and deleting an agent in the DB."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Create
        new_agent = {
            "name": "TestAgent",
            "role": "Tester",
            "system_prompt": "You test things.",
            "model_provider": "openai",
            "model_tier": "fast",
            "capabilities": ["testing"],
        }
        resp = await ac.post("/agents", json=new_agent)
        assert resp.status_code == 200

        # 2. Update model
        resp = await ac.patch("/agents/TestAgent/model", json={"model_tier": "heavy"})
        assert resp.status_code == 200
        assert resp.json()["config"]["model_tier"] == "heavy"

        # 3. Verify in DB directly
        agents = await db_manager.get_all_agents()
        assert "TestAgent" in agents
        assert agents["TestAgent"]["model_tier"] == "heavy"

        # 4. Delete
        resp = await ac.delete("/agents/TestAgent")
        assert resp.status_code == 200

        agents = await db_manager.get_all_agents()
        assert "TestAgent" not in agents


@pytest.mark.asyncio
async def test_mcp_config_in_db():
    """Verifies adding and removing MCP servers in the DB."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        new_mcp = {
            "name": "CustomMCP",
            "type": "sse",
            "url": "http://localhost:9999",
            "auth_token": "CUSTOM_TOKEN",
        }
        resp = await ac.post("/config/mcp", json=new_mcp)
        assert resp.status_code == 200

        # Verify persistence
        mcp_data = await db_manager.get_mcp_servers()
        assert "CustomMCP" in mcp_data

        # Delete
        resp = await ac.delete("/config/mcp/CustomMCP")
        assert resp.status_code == 200
        mcp_data = await db_manager.get_mcp_servers()
        assert "CustomMCP" not in mcp_data
