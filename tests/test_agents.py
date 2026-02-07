from unittest.mock import MagicMock, patch

import pytest

from src.agents.coder_agent import CoderAgent
from src.agents.research_agent import ResearchAgent


@pytest.fixture
def mock_search_tool():
    # Patch where the class is defined since it is imported locally
    with patch("langchain_community.tools.DuckDuckGoSearchRun") as mock:
        yield mock


@pytest.fixture
def mock_memory_manager():
    # Patch MemoryManager in the module where it is imported globally
    with patch("src.agents.research_agent.MemoryManager") as mock:
        yield mock


def test_research_agent_initialization(mock_search_tool, mock_memory_manager):
    """
    Test that ResearchAgent initializes correctly and registers tools.
    """
    agent = ResearchAgent()
    assert agent.config.name == "ResearchAgent"
    assert "web_search" in agent.tool_functions
    assert "summarize" in agent.tool_functions
    assert "save_memory" in agent.tool_functions
    assert "recall_memory" in agent.tool_functions


def test_coder_agent_initialization():
    """
    Test that CoderAgent initializes correctly and registers tools.
    """
    agent = CoderAgent()
    assert agent.config.name == "CoderAgent"
    assert "write_code" in agent.tool_functions
    assert "execute_code" in agent.tool_functions
    assert "review_code" in agent.tool_functions


@patch("subprocess.run")
def test_coder_agent_execute_code(mock_subprocess):
    """
    Test individual tool logic (mocked execution).
    """
    agent = CoderAgent()
    execute_code = agent.tool_functions["execute_code"]

    # Mock subprocess output
    mock_subprocess.return_value = MagicMock(stdout="Hello Output", stderr="")

    # We need to bypass the file existence check in execute_code
    with patch("os.path.exists", return_value=True):
        result = execute_code("dummy_script.py")

    assert "Hello Output" in result
    mock_subprocess.assert_called_once()
