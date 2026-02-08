import os

import pytest
import yaml
from httpx import ASGITransport, AsyncClient
from server import app


@pytest.mark.asyncio
async def test_list_tools():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.get("/tools")
    assert response.status_code == 200
    tools = response.json()
    assert isinstance(tools, list)
    # Check if some default tools are present
    tool_names = [t["name"] for t in tools]
    assert "web_search" in tool_names or "write_code" in tool_names


@pytest.mark.asyncio
async def test_agent_lifecycle():
    agent_name = "DashboardTestBot"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Create
        response = await ac.post(
            "/agents",
            json={
                "name": agent_name,
                "role": "Tester",
                "system_prompt": "You are a test bot.",
                "capabilities": ["testing"],
                "model_provider": "google",
                "model_tier": "fast",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "created"

        # 2. Update
        response = await ac.put(
            f"/agents/{agent_name}",
            json={
                "role": "Senior Tester",
                "system_prompt": "You are a senior test bot.",
            },
        )
        assert response.status_code == 200
        assert response.json()["config"]["role"] == "Senior Tester"

        # 3. Delete
        response = await ac.delete(f"/agents/{agent_name}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify persistence (it should be gone now using the GET endpoint)
        response = await ac.get("/agents")
        assert response.status_code == 200
        agents = response.json()
        assert agent_name not in agents
