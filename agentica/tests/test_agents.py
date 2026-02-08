from unittest.mock import MagicMock, patch

import pytest
from src.agents.coder_agent import CoderAgent
from src.agents.research_agent import ResearchAgent


class DummyConfig:
    def __init__(self, name):
        self.name = name
        self.agent_id = f"test_{name}"
        self.model_provider = "google"
        self.model_tier = "fast"
        self.system_prompt = f"{name} prompt"
        self.tools = []


@pytest.fixture
def mock_search_tool():
    with patch("langchain_community.tools.DuckDuckGoSearchRun") as mock:
        yield mock


@pytest.fixture
def mock_memory_manager():
    with patch("src.agents.research_agent.MemoryManager") as mock:
        yield mock


def test_research_agent_initialization(mock_search_tool, mock_memory_manager):
    """
    Test that ResearchAgent initializes correctly and registers tools.
    """
    config = DummyConfig("ResearchAgent")
    with patch("src.agents.research_agent.load_agent_config", return_value=config):
        agent = ResearchAgent()
        assert agent.config.name == "ResearchAgent"
        assert "web_search" in agent.tool_functions
        assert "summarize" in agent.tool_functions


def test_coder_agent_initialization():
    """
    Test that CoderAgent initializes correctly and registers tools.
    """
    config = DummyConfig("CoderAgent")
    with patch("src.agents.coder_agent.load_agent_config", return_value=config):
        agent = CoderAgent()
        assert agent.config.name == "CoderAgent"
        assert "write_code" in agent.tool_functions
        assert "execute_code" in agent.tool_functions
        assert "create_tool" in agent.tool_functions


@patch("subprocess.run")
def test_coder_agent_execute_code(mock_subprocess):
    """
    Test individual tool logic (mocked execution).
    """
    config = DummyConfig("CoderAgent")
    with patch("src.agents.coder_agent.load_agent_config", return_value=config):
        agent = CoderAgent()
        execute_code = agent.tool_functions["execute_code"]

        mock_subprocess.return_value = MagicMock(stdout="Hello Output", stderr="")

        with patch("os.path.exists", return_value=True):
            result = execute_code("dummy_script.py")

        assert "Hello Output" in result
        mock_subprocess.assert_called_once()
