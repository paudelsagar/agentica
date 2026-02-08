from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.data_agent import DataAgent


@pytest.fixture
def mock_toolbox_available():
    with patch("src.agents.data_agent.TOOLBOX_AVAILABLE", True):
        yield


@pytest.fixture
def mock_toolbox_client():

    with patch("src.agents.data_agent.ToolboxClient") as mock:
        yield mock


@pytest.fixture
def mock_toolbox_tool():
    tool = MagicMock()
    tool._name = "test_tool"
    tool.__name__ = "test_tool"

    # Ensure it's awaitable since EnterpriseAgent now checks for it
    async def mock_call(**kwargs):
        return "tool_result"

    tool.__call__ = mock_call
    return tool


def test_data_agent_initialization():
    """Test that DataAgent initializes correctly."""
    agent = DataAgent()
    assert agent.config.name == "DataAgent"
    assert agent._tools_loaded is False


@pytest.mark.asyncio
async def test_data_agent_tool_loading(
    mock_toolbox_available, mock_toolbox_client, mock_toolbox_tool
):
    """Test that tools are loaded and registered from the Toolbox server."""
    agent = DataAgent()

    # Mock load_toolset to return a list of tools
    mock_client_instance = mock_toolbox_client.return_value
    mock_client_instance.load_toolset = AsyncMock(return_value=[mock_toolbox_tool])

    # Trigger tool loading
    await agent._load_toolbox_tools()

    assert agent._tools_loaded is True
    assert "test_tool" in agent.tool_functions
    mock_client_instance.load_toolset.assert_called_once()


@pytest.mark.asyncio
async def test_data_agent_call_triggers_loading(
    mock_toolbox_available, mock_toolbox_client, mock_toolbox_tool
):
    """Test that calling the agent triggers lazy tool loading."""
    agent = DataAgent()

    mock_client_instance = mock_toolbox_client.return_value
    mock_client_instance.load_toolset = AsyncMock(return_value=[mock_toolbox_tool])

    # Mock super().__call__ to avoid actual LLM invocation
    with patch(
        "src.core.agent.EnterpriseAgent.__call__", new_callable=AsyncMock
    ) as mock_super_call:
        mock_super_call.return_value = {"messages": [], "next_agent": "END"}

        await agent({"messages": []})

        assert agent._tools_loaded is True
        assert "test_tool" in agent.tool_functions
        mock_super_call.assert_called_once()
