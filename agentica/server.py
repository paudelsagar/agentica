import os
from typing import Any, Dict, List

import aiosqlite
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv(dotenv_path=".env")

from fastapi import FastAPI, HTTPException
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from src.agents.data_agent import DataAgent
from src.agents.research_agent import ResearchAgent
from src.core.consensus import consensus_manager
from src.core.graph import AgentState
from src.core.logger import configure_logger, get_logger
from src.core.registry import tool_registry
from src.core.supervisor import SupervisorAgent
from src.core.teams import dev_team_node
from src.core.usage import usage_tracker

# Configure logging
configure_logger()
logger = get_logger(__name__)

app = FastAPI(title="Agentic AI Enterprise Server")

# Initialize Agents
supervisor = SupervisorAgent()
researcher = ResearchAgent()
data_agent = DataAgent()

# Build Graph
workflow = StateGraph(AgentState)
workflow.add_node("SupervisorAgent", supervisor)
workflow.add_node("ResearchAgent", researcher)
workflow.add_node("DataAgent", data_agent)
workflow.add_node("DevTeam", dev_team_node)

workflow.set_entry_point("SupervisorAgent")


# Error Analyzer Node for Self-Healing
def error_analyzer(state: AgentState):
    """
    Scans the conversation for errors and triggers retries if possible.
    """
    messages = state.get("messages", [])
    retry_data = state.get("retry_data", {})

    if not messages:
        return {"next_agent": "JoinParallel"}

    last_msg = messages[-1]

    # Simple check for error markers in ToolMessages
    if hasattr(last_msg, "content") and "Error:" in str(last_msg.content):
        # Determine which agent failed
        failed_agent = getattr(last_msg, "name", "UnknownAgent")
        current_retries = retry_data.get(failed_agent, 0)

        if current_retries < 2:
            logger.warning(
                "error_detected_triggering_retry",
                agent=failed_agent,
                retry=current_retries + 1,
            )
            retry_msg = SystemMessage(
                content=f"ALERT: Your previous action failed with an error. Please re-examine the error message carefully and try a different approach or fix the syntax: {last_msg.content}"
            )
            return {
                "messages": [retry_msg],
                "next_agent": "RETRY",
                "retry_data": {failed_agent: current_retries + 1},
            }
        else:
            logger.error("max_retries_reached", agent=failed_agent)

    return {"next_agent": "JoinParallel"}


workflow.add_node("ErrorAnalyzer", error_analyzer)


# Human-In-The-Loop (HITL) Security Layer
def hitl_gate(state: AgentState):
    """
    Gatekeeper that decides if a task needs manual approval.
    """
    messages = state.get("messages", [])
    next_agent = state.get("next_agent", "FINISH")

    logger.info("hitl_gate_check", next_agent=next_agent)

    last_msg = ""
    if messages:
        last_msg = str(messages[-1].content).upper()

    approval_required = False
    if "WAIT FOR APPROVAL" in last_msg or "APPROVE?" in last_msg:
        approval_required = True
    elif isinstance(next_agent, list):
        if any("CODERAGENT" in str(a).upper() for a in next_agent):
            approval_required = True
    elif any(x in str(next_agent).upper() for x in ["CODERAGENT", "DEVTEAM"]):
        approval_required = True

    if approval_required:
        logger.warning("hitl_gate_approval_required", next_agent=next_agent)
        # Store the intended agent so we can recover it after pause
        return {"intended_agent": str(next_agent), "next_agent": "HITL_PAUSE"}

    return {"intended_agent": str(next_agent), "next_agent": next_agent}


def hitl_pause(state: AgentState):
    """
    Dummy node used as a static interrupt point.
    Graph will pause BEFORE this node. When resumed, it proceeds to specialists.
    """
    logger.info("hitl_pause_executed_resuming_to_specials")
    return {}


workflow.add_node("HITLGate", hitl_gate)
workflow.add_node("HITLPause", hitl_pause)


# Join Node for parallel synchronization


def join_parallel(state: AgentState):
    """
    Consolidates parallel branches. Wait until wait_count is 0.
    """
    wait_count = state.get("wait_count", 0)
    requires_consensus = state.get("require_consensus", False)
    logger.info(
        "join_parallel_check",
        wait_count=wait_count,
        requires_consensus=requires_consensus,
    )

    if wait_count <= 0:
        if requires_consensus:
            return {"next_agent": "ConsensusNode"}
        return {"next_agent": "SupervisorAgent"}
    return {"next_agent": "JOIN"}


def consensus_node(state: AgentState):
    """
    Evaluates votes from multiple agents to reach a consensus.
    """
    messages = state.get("messages", [])
    intended = state.get("intended_agent", "")

    # Recover agents list
    agents_list = []
    try:
        if intended.startswith("["):
            import ast

            agents_list = ast.literal_eval(intended)
        else:
            agents_list = [intended]
    except:
        pass

    votes = []
    for agent_name in agents_list:
        for msg in reversed(messages):
            if getattr(msg, "name", "") == agent_name:
                vote = consensus_manager.parse_vote(agent_name, str(msg.content))
                votes.append(vote)
                break

    result = consensus_manager.evaluate(votes)
    summary_msg = SystemMessage(
        content=f"CONSENSUS REPORT: {result.summary}\nMET: {result.consensus_met}"
    )

    return {
        "messages": [summary_msg],
        "require_consensus": False,
        "next_agent": "SupervisorAgent",
    }


workflow.add_node("JoinParallel", join_parallel)
workflow.add_node("ConsensusNode", consensus_node)
workflow.add_conditional_edges("ConsensusNode", lambda x: "SupervisorAgent")


def supervisor_router(state):
    next_agent = state.get("next_agent", "FINISH")
    logger.info("supervisor_router_called", next_agent=next_agent)

    # Coerce list to string if it's a single element like ['FINISH']
    if isinstance(next_agent, list):
        if len(next_agent) == 1:
            next_agent = next_agent[0]
        else:
            # Parallel tasks always go through HITLGate
            logger.info("supervisor_router_returns", result="HITLGate")
            return "HITLGate"

    if next_agent == "FINISH" or next_agent == "END":
        logger.info("supervisor_router_returns", result="END")
        return "END"

    # All agent tasks go through HITLGate first for dynamic pause checks
    logger.info("supervisor_router_returns", result="HITLGate")
    return "HITLGate"


workflow.add_conditional_edges(
    "SupervisorAgent",
    supervisor_router,
    {"HITLGate": "HITLGate", "END": END},
)


def gate_router(state):
    next_agent = state.get("next_agent", "FINISH")
    intended_agent = state.get("intended_agent", next_agent)
    logger.info(
        "gate_router_called", next_agent=next_agent, intended_agent=intended_agent
    )

    if next_agent == "HITL_PAUSE":
        return "HITLPause"

    # For autonomous flow, next_agent is already the specialist (string or list)
    return next_agent


workflow.add_conditional_edges(
    "HITLGate",
    gate_router,
    {
        "HITLPause": "HITLPause",
        "ResearchAgent": "ResearchAgent",
        "DataAgent": "DataAgent",
        "DevTeam": "DevTeam",
        "FINISH": END,
    },
)


def pause_router(state):
    # This node only runs AFTER a resume from interrupt_before=["HITLPause"]
    # We recover the actual destination from intended_agent
    intended_agent = state.get("intended_agent", "FINISH")
    logger.info("pause_router_called", intended_agent=intended_agent)

    # next_agent could be a string like "CoderAgent" or a list like ["CoderAgent"]
    # We need to return exactly what the mapping expects.
    # If intended_agent is a string representation of a list, careful.
    # But Supervisor returns a list, and hitl_gate does str(next_agent).

    # Let's handle stringified lists if any
    if intended_agent.startswith("[") and intended_agent.endswith("]"):
        import ast

        try:
            return ast.literal_eval(intended_agent)
        except Exception:
            return intended_agent

    return intended_agent


workflow.add_conditional_edges(
    "HITLPause",
    pause_router,
    {
        "ResearchAgent": "ResearchAgent",
        "DataAgent": "DataAgent",
        "DevTeam": "DevTeam",
        "FINISH": END,
    },
)


def worker_router(state):
    next_agent = state.get("next_agent", "END")
    logger.info("worker_router_called", next_agent=next_agent)

    if next_agent == "END" or next_agent == "FINISH":
        # In hierarchical mode, workers return to the Supervisor to verify progress
        result = "SupervisorAgent"
    else:
        # If worker requested another tool/agent (though unlikely in this design)
        result = next_agent

    logger.info("worker_router_returns", result=result)
    return result


workflow.add_conditional_edges("ResearchAgent", worker_router)
workflow.add_conditional_edges("DataAgent", worker_router)
workflow.add_conditional_edges("DevTeam", worker_router)


def error_router(state):
    next_agent = state.get("next_agent", "JoinParallel")
    logger.info("error_router_called", next_agent=next_agent)

    result = "JoinParallel"
    if next_agent == "RETRY":
        result = "SupervisorAgent"

    logger.info("error_router_returns", result=result)
    return result


workflow.add_conditional_edges(
    "ErrorAnalyzer",
    error_router,
    {"SupervisorAgent": "SupervisorAgent", "JoinParallel": "JoinParallel"},
)


def join_router(state):
    next_agent = state.get("next_agent", "SupervisorAgent")
    logger.info("join_router_called", next_agent=next_agent)

    if next_agent == "JOIN":
        logger.info("join_router_returns", result="__end__")
        return "__end__"

    if next_agent == "ConsensusNode":
        return "ConsensusNode"

    logger.info("join_router_returns", result="SupervisorAgent")
    return "SupervisorAgent"


workflow.add_conditional_edges(
    "JoinParallel",
    join_router,
    {
        "SupervisorAgent": "SupervisorAgent",
        "ConsensusNode": "ConsensusNode",
        "__end__": END,
    },
)


# Setup Persistence
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "state.db")


class RunRequest(BaseModel):
    thread_id: str
    message: str


@app.post("/run")
async def run_workflow(request: RunRequest):
    logger.info(
        "received_request", thread_id=request.thread_id, message=request.message
    )

    config = {"configurable": {"thread_id": request.thread_id}}
    input_message = HumanMessage(content=request.message)

    final_output = []

    try:
        # Use AsyncSqliteSaver as a context manager for each request
        async with aiosqlite.connect(DB_PATH) as conn:
            checkpointer = AsyncSqliteSaver(conn)
            # Compile with interrupt on the HITL pause point
            app_graph = workflow.compile(
                checkpointer=checkpointer, interrupt_before=["HITLPause"]
            )

            async for event in app_graph.astream(
                {
                    "messages": [input_message],
                    "plan": [],
                    "plan_step": 0,
                    "task_context": request.message,
                    "wait_count": 0,
                    "retry_data": {},
                    "intended_agent": "",
                    "require_consensus": False,
                },
                config,
                stream_mode="values",
            ):

                if "messages" in event:
                    final_output = event["messages"]
    except Exception as e:
        logger.error("workflow_failed", error=str(e))
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    # Determine status based on snapshot
    status = "success"
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            checkpointer = AsyncSqliteSaver(conn)
            app_graph = workflow.compile(checkpointer=checkpointer)
            snapshot = await app_graph.aget_state(config)
            if snapshot.next:
                status = "requires_action"
    except Exception:
        pass

    # Extract the last AIMessage content for response
    last_response = ""
    if final_output:
        last_msg = final_output[-1]
        content = getattr(last_msg, "content", "")
        if isinstance(content, list):
            # Extract text from blocks
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
                elif isinstance(part, str):
                    text_parts.append(part)
            last_response = "\n".join(text_parts)
        else:
            last_response = str(content)

    return {
        "thread_id": request.thread_id,
        "status": status,
        "last_message": last_response,
    }


@app.post("/approve")
async def approve_workflow(request: RunRequest):
    """
    Resumes a paused workflow.
    """
    logger.info("received_approval", thread_id=request.thread_id)
    config = {"configurable": {"thread_id": request.thread_id}}

    final_output = []

    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            checkpointer = AsyncSqliteSaver(conn)
            # Compile WITHOUT interrupt to allow full execution upon approval
            app_graph = workflow.compile(checkpointer=checkpointer)

            # Resume by passing None (triggered by state update or just resume)
            # effectively continuing from the interruption.
            async for event in app_graph.astream(None, config, stream_mode="values"):
                if "messages" in event:
                    final_output = event["messages"]
    except Exception as e:
        logger.error("approval_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

    last_response = ""
    if final_output:
        last_msg = final_output[-1]
        content = getattr(last_msg, "content", "")
        if isinstance(content, list):
            # Extract text from blocks
            text_parts = []
            for part in content:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
                elif isinstance(part, str):
                    text_parts.append(part)
            last_response = "\n".join(text_parts)
        else:
            last_response = str(content)

    return {
        "thread_id": request.thread_id,
        "status": "success",
        "last_message": last_response,
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/metrics")
async def get_metrics():
    """Returns aggregated performance metrics."""
    return await usage_tracker.get_metrics()


@app.get("/tools")
def list_tools():
    """Returns all globally registered tools."""
    tools = tool_registry.list_tools()
    return [
        {"name": t.name, "description": t.description, "owner": t.owner_agent}
        for t in tools
    ]


@app.get("/state/{thread_id}")
async def get_state(thread_id: str):
    """Retrieves the current workflow state for a thread."""
    config = {"configurable": {"thread_id": thread_id}}
    async with aiosqlite.connect(DB_PATH) as conn:
        checkpointer = AsyncSqliteSaver(conn)
        app_graph = workflow.compile(checkpointer=checkpointer)
        snapshot = await app_graph.aget_state(config)
        return {
            "values": snapshot.values,
            "next": snapshot.next,
            "metadata": snapshot.metadata,
        }


@app.get("/trajectories/{thread_id}")
async def get_trajectories(thread_id: str):
    """Returns execution history for a thread."""
    async with aiosqlite.connect(DB_PATH) as conn:
        async with conn.execute(
            "SELECT agent_name, input, output, success, timestamp FROM trajectories WHERE thread_id = ? ORDER BY timestamp ASC",
            (thread_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [
                {
                    "agent": r[0],
                    "input": r[1],
                    "output": r[2],
                    "success": bool(r[3]),
                    "timestamp": r[4],
                }
                for r in rows
            ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
