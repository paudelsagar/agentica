from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from src.core.supervisor import SupervisorAgent


def mock_supervisor_init(self):
    self.config = MagicMock()
    self.config.name = "SupervisorAgent"
    self.config.agent_id = "test_id"
    self.config.model_provider = "google"
    self.config.model_tier = "fast"
    self.config.system_prompt = "Supervisor prompt"
    self.log = MagicMock()
    self.llm = AsyncMock()
    # Mock base class methods
    self._recall_context = AsyncMock(return_value="")
    self._reflect_and_store = AsyncMock()
    self.tool_functions = {}


@pytest.mark.asyncio
async def test_supervisor_parsing_multi_agent():
    # Patch __init__ to avoid loading actual config/LLM
    with patch.object(SupervisorAgent, "__init__", mock_supervisor_init), patch(
        "src.core.supervisor.tool_registry.list_tools", return_value=[]
    ), patch("src.core.supervisor.usage_tracker.record_usage"):

        supervisor = SupervisorAgent()
        # Mock LLM response with multiple NEXT AGENT lines
        mock_response = AIMessage(
            content="Plan:\n1. Search\n2. Code\nNEXT AGENT: ResearchAgent\nNEXT AGENT: CoderAgent"
        )
        supervisor.llm.ainvoke = AsyncMock(return_value=mock_response)

        state = {"messages": [], "plan": [], "plan_step": 0}
        result = await supervisor(state)

        assert "ResearchAgent" in result["next_agent"]
        assert "CoderAgent" in result["next_agent"]
        assert result["wait_count"] == 2
        assert result["require_consensus"] is False


@pytest.mark.asyncio
async def test_supervisor_parsing_comma_separated():
    with patch.object(SupervisorAgent, "__init__", mock_supervisor_init), patch(
        "src.core.supervisor.tool_registry.list_tools", return_value=[]
    ), patch("src.core.supervisor.usage_tracker.record_usage"):

        supervisor = SupervisorAgent()
        mock_response = AIMessage(content="NEXT AGENT: DataAgent, ResearchAgent")
        supervisor.llm.ainvoke = AsyncMock(return_value=mock_response)

        state = {"messages": [], "plan": [], "plan_step": 0}
        result = await supervisor(state)

        assert "DataAgent" in result["next_agent"]
        assert "ResearchAgent" in result["next_agent"]
        assert result["wait_count"] == 2


@pytest.mark.asyncio
async def test_supervisor_parsing_critical_flag():
    with patch.object(SupervisorAgent, "__init__", mock_supervisor_init), patch(
        "src.core.supervisor.tool_registry.list_tools", return_value=[]
    ), patch("src.core.supervisor.usage_tracker.record_usage"):

        supervisor = SupervisorAgent()
        # "CRITICAL" + multiple agents should trigger require_consensus
        mock_response = AIMessage(
            content="CRITICAL: Deleting backup.\nNEXT AGENT: ResearchAgent, CoderAgent"
        )
        supervisor.llm.ainvoke = AsyncMock(return_value=mock_response)

        state = {"messages": [], "plan": [], "plan_step": 0}
        result = await supervisor(state)

        assert result["require_consensus"] is True
        assert len(result["next_agent"]) == 2


@pytest.mark.asyncio
async def test_supervisor_parsing_finish():
    with patch.object(SupervisorAgent, "__init__", mock_supervisor_init), patch(
        "src.core.supervisor.tool_registry.list_tools", return_value=[]
    ), patch("src.core.supervisor.usage_tracker.record_usage"):

        supervisor = SupervisorAgent()
        mock_response = AIMessage(content="Task complete. NEXT AGENT: FINISH")
        supervisor.llm.ainvoke = AsyncMock(return_value=mock_response)

        state = {"messages": [], "plan": [], "plan_step": 0}
        result = await supervisor(state)

        assert result["next_agent"] == ["FINISH"]
        assert result["wait_count"] == 0
