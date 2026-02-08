import os

import pytest
import yaml
from httpx import ASGITransport, AsyncClient
from server import app


@pytest.mark.asyncio
async def test_add_mcp_server():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post(
            "/config/mcp",
            json={
                "name": "TestMCP",
                "type": "sse",
                "url": "http://localhost:1234",
                "auth_token_env": "TEST_TOKEN",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["server"] == "TestMCP"
        assert data["config"]["url"] == "http://localhost:1234"

        # Verify persistence via GET endpoint
        response = await ac.get("/mcp/servers")
        assert response.status_code == 200
        servers = response.json()
        assert "TestMCP" in servers
        assert servers["TestMCP"]["url"] == "http://localhost:1234"


@pytest.mark.asyncio
async def test_delete_mcp_server():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Delete
        response = await ac.delete("/config/mcp/TestMCP")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify persistence via GET endpoint
        response = await ac.get("/mcp/servers")
        assert response.status_code == 200
        servers = response.json()
        assert "TestMCP" not in servers
