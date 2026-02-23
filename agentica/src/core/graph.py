import operator
from typing import Annotated, Any, Dict, List, TypedDict, Union

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph


class AgentState(TypedDict):
    """
    The state of the agent system.
    """

    messages: Annotated[List[BaseMessage], operator.add]
    # Simple reducer: last write wins (or any non-END value?)
    # For now, we use a simple overwrite reducer to allow parallel agents to write.
    # If multiple write, the last one processed by the reducer wins.
    next_agent: Annotated[Union[str, List[str]], lambda a, b: b]
    task_status: str
    plan: List[str]
    plan_step: int
    task_context: str
    wait_count: Annotated[int, operator.add]
    retry_data: Annotated[Dict[str, int], lambda a, b: {**a, **b}]
    intended_agent: str
    require_consensus: bool
    thinking_mode: bool
    use_web: bool


# We will define the graph builder here, but nodes will be added dynamically
# or imported from agent instances.
def create_graph():
    return StateGraph(AgentState)


def filter_state_for_subgraph(state: AgentState) -> Dict[str, Any]:
    """
    Prepares a subset of state safe to pass to a sub-graph.
    We exclude next_agent to avoid confusion in the child graph's entry point.
    """
    filtered = {k: v for k, v in state.items() if k != "next_agent"}
    return filtered


def merge_agent_state(parent: AgentState, child: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merges sub-graph results back into the parent state.
    Handles additive keys like 'messages' and 'wait_count'.
    """
    merged = dict(parent)

    # 1. Handle messages (already additive in AgentState, but sub-graph returns a full list)
    # We only want the *new* messages from the child
    parent_msg_ids = {id(m) for m in parent.get("messages", [])}
    new_messages = [m for m in child.get("messages", []) if id(m) not in parent_msg_ids]
    if new_messages:
        # parent['messages'] will be updated by the graph's reducer if we return them
        merged["messages"] = new_messages

    # 2. Update Plan and Status if child modified them
    for key in ["plan", "plan_step", "task_status"]:
        if key in child and child[key] != parent.get(key):
            merged[key] = child[key]

    # 3. Propagate wait_count if any
    child_wait = child.get("wait_count", 0)
    if child_wait > 0:
        merged["wait_count"] = child_wait

    return merged
