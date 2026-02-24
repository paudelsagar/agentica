from unittest.mock import AsyncMock, patch

import pytest
from src.agents.data_agent import DataAgent


# Dummy config class to satisfy Pydantic/BaseModel requirements if needed,
# or just a simple class that Agentica can use.
class DummyConfig:
    def __init__(self):
        self.name = "DataAgent"
        self.agent_id = "test_data_agent"
        self.model_provider = "google"
        self.model_tier = "fast"
        self.system_prompt = "Test prompt"
        self.tools = []


@pytest.fixture
def mock_config():
    return DummyConfig()


def test_data_agent_initialization(mock_config):
    """Test that DataAgent initializes correctly."""
    with patch(
        "src.agents.data_agent.load_agent_config", return_value=mock_config
    ), patch("src.core.agent.Agentica._get_llm") as mock_get_llm:
        mock_get_llm.return_value = AsyncMock()
        agent = DataAgent()
        assert agent.config.name == "DataAgent"
        assert agent._tools_loaded is False


@pytest.mark.asyncio
async def test_data_agent_tool_loading(mock_config):
    """Test that tools are loaded via attach_mcp_server."""
    with patch(
        "src.agents.data_agent.load_agent_config", return_value=mock_config
    ), patch("src.core.agent.Agentica._get_llm") as mock_get_llm:
        mock_get_llm.return_value = AsyncMock()
        agent = DataAgent()

        # Mock attach_mcp_server (which is on the base class Agentica)
        with patch.object(
            DataAgent, "attach_mcp_server", new_callable=AsyncMock
        ) as mock_attach:
            await agent._load_toolbox_tools()

            assert agent._tools_loaded is True
            mock_attach.assert_called_once_with("Toolbox")


@pytest.mark.asyncio
async def test_data_agent_call_triggers_loading(mock_config):
    """Test that calling the agent triggers lazy tool loading."""
    with patch(
        "src.agents.data_agent.load_agent_config", return_value=mock_config
    ), patch("src.core.agent.Agentica._get_llm") as mock_get_llm:
        mock_get_llm.return_value = AsyncMock()
        agent = DataAgent()

        # Mock _load_toolbox_tools and super().__call__
        with patch.object(
            agent, "_load_toolbox_tools", new_callable=AsyncMock
        ) as mock_load, patch(
            "src.core.agent.Agentica.__call__", new_callable=AsyncMock
        ) as mock_super_call:

            mock_super_call.return_value = {"messages": [], "next_agent": "FINISH"}

            await agent({"messages": []})

            mock_load.assert_called_once()
            mock_super_call.assert_called_once()
