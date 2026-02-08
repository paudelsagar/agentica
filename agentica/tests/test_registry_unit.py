import pytest
from src.core.registry import ToolEntry, ToolRegistry


def test_registry_register_and_list():
    registry = (
        ToolRegistry()
    )  # It's a singleton internally, but let's test a fresh instance if possible
    # Note: ToolRegistry is likely a singleton in registry.py.
    # Let's clear it if needed or just test the current state.

    registry.register_tool(
        ToolEntry(name="test_tool", description="description", owner_agent="AgentA")
    )
    tools = registry.list_tools()

    registered = [t for t in tools if t.name == "test_tool"]
    assert len(registered) == 1
    assert registered[0].owner_agent == "AgentA"


def test_registry_prevent_duplicate_different_owner():
    registry = ToolRegistry()
    registry.register_tool(
        ToolEntry(name="shared_tool", description="desc1", owner_agent="AgentA")
    )
    # Registering same name with different owner should update or ignore?
    # Usually we want to know who owns what.
    registry.register_tool(
        ToolEntry(name="shared_tool", description="desc2", owner_agent="AgentB")
    )

    tools = registry.list_tools()
    matches = [t for t in tools if t.name == "shared_tool"]
    # If the implementation replaces:
    assert len(matches) == 1
    assert matches[0].owner_agent == "AgentB"


def test_registry_list_by_agent():
    registry = ToolRegistry()
    registry.register_tool(
        ToolEntry(name="tool1", description="d1", owner_agent="AgentX")
    )
    registry.register_tool(
        ToolEntry(name="tool2", description="d2", owner_agent="AgentX")
    )
    registry.register_tool(
        ToolEntry(name="tool3", description="d3", owner_agent="AgentY")
    )

    agent_x_tools = [t for t in registry.list_tools() if t.owner_agent == "AgentX"]
    assert len(agent_x_tools) == 2
    assert "tool1" in [t.name for t in agent_x_tools]
    assert "tool2" in [t.name for t in agent_x_tools]
