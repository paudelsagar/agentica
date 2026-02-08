import pytest


@pytest.mark.asyncio
async def test_list_agents(async_client):
    response = await async_client.get("/agents")
    assert response.status_code == 200
    agents = response.json()
    assert "SupervisorAgent" in agents
    assert "ResearchAgent" in agents


@pytest.mark.asyncio
async def test_list_mcp_servers(async_client):
    response = await async_client.get("/mcp/servers")
    assert response.status_code == 200
    servers = response.json()
    assert isinstance(servers, dict)


@pytest.mark.asyncio
async def test_memory_search(async_client):
    response = await async_client.get(
        "/memory/search", params={"query": "test", "k": 1}
    )
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert "results" in data


@pytest.mark.asyncio
async def test_delete_state(async_client):
    response = await async_client.delete("/state/test_thread_123")
    assert response.status_code == 200
    assert response.json() == {"status": "deleted", "thread_id": "test_thread_123"}
