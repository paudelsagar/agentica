import operator
from typing import Annotated, Any, Dict, List, TypedDict, Union

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph


class AgentState(TypedDict):
    """
    The state of the agent system.
    """

    messages: Annotated[List[BaseMessage], operator.add]
    next_agent: str
    task_status: str


# We will define the graph builder here, but nodes will be added dynamically
# or imported from agent instances.
def create_graph():
    return StateGraph(AgentState)
