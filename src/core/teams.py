from langgraph.graph import END, StateGraph

from src.agents.coder_agent import CoderAgent
from src.agents.dev_lead_agent import DevLeadAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.core.graph import AgentState
from src.core.logger import get_logger

logger = get_logger(__name__)

# Initialize team members
dev_lead = DevLeadAgent()
coder = CoderAgent()
reviewer = ReviewerAgent()


from langchain_core.runnables import RunnableConfig


async def dev_lead_node(state: AgentState, config: RunnableConfig):
    print("\n>>> [TEAM] DevLead executing...")
    logger.info("dev_lead_executing")
    return await dev_lead(state, config)


async def coder_node(state: AgentState, config: RunnableConfig):
    print(">>> [TEAM] Coder executing...")
    logger.info("coder_executing_in_team")
    return await coder(state, config)


async def reviewer_node(state: AgentState, config: RunnableConfig):
    print(">>> [TEAM] Reviewer executing...")
    logger.info("reviewer_executing_in_team")
    return await reviewer(state, config)


def dev_team_router(state: AgentState):
    next_agent = state.get("next_agent", "FINISH")
    logger.info("dev_team_router_called", next_agent=next_agent)

    if next_agent == "CoderAgent":
        return "CoderAgent"
    if next_agent == "ReviewerAgent":
        return "ReviewerAgent"

    return END


def create_dev_team_graph():
    """
    Creates a nested graph for the development team.
    """
    team_workflow = StateGraph(AgentState)

    team_workflow.add_node("DevLead", dev_lead_node)
    team_workflow.add_node("CoderAgent", coder_node)
    team_workflow.add_node("ReviewerAgent", reviewer_node)

    team_workflow.set_entry_point("DevLead")

    team_workflow.add_conditional_edges(
        "DevLead",
        dev_team_router,
        {"CoderAgent": "CoderAgent", "ReviewerAgent": "ReviewerAgent", END: END},
    )

    # After specialists finish, they always go back to the lead
    team_workflow.add_edge("CoderAgent", "DevLead")
    team_workflow.add_edge("ReviewerAgent", "DevLead")

    return team_workflow.compile()


from src.core.graph import filter_state_for_subgraph, merge_agent_state


async def dev_team_node_func(state: AgentState, config: RunnableConfig):
    """
    Invokes the dev team sub-graph and synchronizes state back to the parent.
    """
    logger.info("dev_team_subgraph_invoked")

    # 1. Filter state for child (ensure it enters at DevLead)
    child_state = filter_state_for_subgraph(state)

    # 2. Invoke sub-graph
    team_graph = create_dev_team_graph()
    result = await team_graph.ainvoke(child_state, config=config)

    # 3. Merge results back strictly
    # We want to keep the parent's context but add the team's updates
    # and decide where the main graph goes next (usually it was DevTeam -> END in server.py)
    # but the router will decide that.
    merged = merge_agent_state(state, result)

    # Ensure next_agent from SUBGRAPH (which is END) doesn't kill the MAIN graph
    # unless intended. Supervisor usually handles this, but let's be safe.
    # The sub-graph finishes with next_agent: END, which we want to map to
    # the MAIN graph's next step.

    return merged


# Export the function instead of the raw compiled graph
dev_team_node = dev_team_node_func
