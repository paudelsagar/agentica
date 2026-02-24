"""Tests for the Supervisor's intent classifier and agent capability registry."""

from unittest.mock import MagicMock, patch

import pytest
from src.core.supervisor import AGENT_CAPABILITIES, SupervisorAgent


def mock_supervisor_init(self):
    self.config = MagicMock()
    self.config.name = "SupervisorAgent"
    self.config.agent_id = "test_id"
    self.config.model_provider = "google"
    self.config.model_tier = "fast"
    self.config.system_prompt = "Supervisor prompt"
    self.log = MagicMock()
    self.llm = MagicMock()
    self._recall_context = MagicMock()
    self._reflect_and_store = MagicMock()
    self.tool_functions = {}


def _make_supervisor():
    with patch.object(SupervisorAgent, "__init__", mock_supervisor_init):
        return SupervisorAgent()


# --- Agent Capabilities Registry ---


def test_all_agents_have_required_keys():
    for agent_name, caps in AGENT_CAPABILITIES.items():
        assert "description" in caps, f"{agent_name} missing description"
        assert "triggers" in caps, f"{agent_name} missing triggers"
        assert "tools" in caps, f"{agent_name} missing tools"
        assert len(caps["triggers"]) > 0, f"{agent_name} has no triggers"


def test_expected_agents_present():
    assert "DataAgent" in AGENT_CAPABILITIES
    assert "ResearchAgent" in AGENT_CAPABILITIES
    assert "DevTeam" in AGENT_CAPABILITIES


# --- DataAgent routing ---


def test_classify_data_merchants():
    s = _make_supervisor()
    assert s._classify_intent("list travel related merchants") == "DataAgent"


def test_classify_data_users():
    s = _make_supervisor()
    assert s._classify_intent("show me all users") == "DataAgent"


def test_classify_data_transactions():
    s = _make_supervisor()
    assert s._classify_intent("list last 10 transactions of user U1003") == "DataAgent"


def test_classify_data_kyc():
    s = _make_supervisor()
    assert s._classify_intent("list users with pending KYC status") == "DataAgent"


def test_classify_data_accounts():
    s = _make_supervisor()
    assert s._classify_intent("show active accounts") == "DataAgent"


def test_classify_data_report():
    s = _make_supervisor()
    assert s._classify_intent("daily transaction summary report") == "DataAgent"


# --- ResearchAgent routing ---


def test_classify_research_weather():
    s = _make_supervisor()
    assert s._classify_intent("what is the weather in Kathmandu") == "ResearchAgent"


def test_classify_research_news():
    s = _make_supervisor()
    assert s._classify_intent("latest news about AI") == "ResearchAgent"


def test_classify_research_price():
    s = _make_supervisor()
    assert s._classify_intent("current bitcoin price") == "ResearchAgent"


def test_classify_research_howto():
    s = _make_supervisor()
    assert (
        s._classify_intent("how to search for deploying a docker container")
        == "ResearchAgent"
    )


# --- DevTeam routing ---


def test_classify_dev_write_code():
    s = _make_supervisor()
    assert (
        s._classify_intent("write code for a python script to sort a list") == "DevTeam"
    )


def test_classify_dev_debug():
    s = _make_supervisor()
    assert s._classify_intent("debug the failing test function") == "DevTeam"


def test_classify_dev_refactor():
    s = _make_supervisor()
    assert s._classify_intent("refactor the code in main.py") == "DevTeam"


# --- Ambiguous / None ---


def test_ambiguous_returns_none():
    s = _make_supervisor()
    assert s._classify_intent("hello") is None


def test_single_keyword_returns_none():
    s = _make_supervisor()
    assert s._classify_intent("explain") is None
