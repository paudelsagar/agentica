import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiosqlite
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv(dotenv_path=".env")

from src.core.logger import configure_logger, get_logger

# Configure logging before any other core imports
configure_logger()
logger = get_logger(__name__)

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from src.agents.data_agent import DataAgent
from src.agents.research_agent import ResearchAgent
from src.core.config import load_agent_config
from src.core.consensus import consensus_manager
from src.core.db_manager import db_manager
from src.core.graph import AgentState
from src.core.mcp import mcp_router
from src.core.model_router import model_router
from src.core.prompt_optimizer import optimizer
from src.core.registry import tool_registry
from src.core.supervisor import SupervisorAgent
from src.core.teams import dev_team_node
from src.core.usage import usage_tracker

# Setup Persistence
DATABASE_STATE_PATH = os.path.join(os.path.dirname(__file__), "data", "state.db")


def filter_agent_content(content: str) -> str:
    """
    Filter agent content to extract only the human-readable summary.
    Handles multiple formats:
    - "SUMMARY: text [END_SUMMARY] PLAN:..." -> extracts "text"
    - "I'll check... [END_SUMMARY] PLAN:..." -> extracts "I'll check..."
    - "text PLAN: ..." -> extracts "text"
    """
    filtered = content

    # First check if SUMMARY: prefix exists and extract content after it
    summary_upper = filtered.upper()
    if "SUMMARY:" in summary_upper:
        idx = summary_upper.find("SUMMARY:")
        filtered = filtered[idx + 8 :]  # 8 = len("SUMMARY:")

    # Find the earliest technical marker and cut there
    # These markers indicate the start of non-user-facing content
    markers = ["[END_SUMMARY]", "PLAN:", "NEXT AGENT:", "DELEGATION:", "```tool_code"]
    end_idx = len(filtered)
    for marker in markers:
        idx = (
            filtered.upper().find(marker.upper())
            if marker != "```tool_code"
            else filtered.find(marker)
        )
        if idx != -1:
            end_idx = min(end_idx, idx)

    return filtered[:end_idx].strip()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes the database and refreshes all dynamic configurations."""
    from src.core.config import refresh_agent_configs

    await db_manager.initialize()
    await refresh_agent_configs()
    await model_router.refresh_config()
    await mcp_router.refresh_config()

    global supervisor, researcher, data_agent
    # Initialize agents (now they will use the DB cache)
    supervisor = SupervisorAgent()
    researcher = ResearchAgent()
    data_agent = DataAgent()

    # Rebuild and compile the graph with an active checkpointer
    async with AsyncSqliteSaver.from_conn_string(DATABASE_STATE_PATH) as saver:
        await build_graph(saver)
        logger.info("server_dynamic_configs_initialized")
        yield


app = FastAPI(
    title="Agentica Server",
    description="Multi-Agent Orchestration System using LangGraph and MCP",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


def gate_router(state):
    next_agent = state.get("next_agent", "FINISH")
    intended_agent = state.get("intended_agent", next_agent)
    logger.info(
        "gate_router_called", next_agent=next_agent, intended_agent=intended_agent
    )

    if next_agent == "HITL_PAUSE":
        return "HITLPause"

    # Normalize END to FINISH for consistent graph routing
    if next_agent == "END" or next_agent == ["FINISH"]:
        return "FINISH"

    # For autonomous flow, next_agent is already the specialist (string or list)
    return next_agent


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


def error_router(state):
    next_agent = state.get("next_agent", "JoinParallel")
    logger.info("error_router_called", next_agent=next_agent)

    result = "JoinParallel"
    if next_agent == "RETRY":
        result = "SupervisorAgent"

    logger.info("error_router_returns", result=result)
    return result


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


async def build_graph(saver):
    """Initializes agents and builds the LangGraph workflow."""
    global supervisor, researcher, data_agent, workflow_app

    # Initialize agents
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

    # Nodes
    workflow.add_node("ErrorAnalyzer", error_analyzer)
    workflow.add_node("HITLGate", hitl_gate)
    workflow.add_node("HITLPause", hitl_pause)
    workflow.add_node("JoinParallel", join_parallel)
    workflow.add_node("ConsensusNode", consensus_node)

    # Edges
    workflow.add_edge("ResearchAgent", "HITLGate")
    workflow.add_edge("DataAgent", "HITLGate")
    workflow.add_edge("DevTeam", "HITLGate")

    # Conditional Edges
    workflow.add_conditional_edges(
        "SupervisorAgent",
        supervisor_router,
        {"HITLGate": "HITLGate", "END": END},
    )

    workflow.add_conditional_edges(
        "HITLGate",
        gate_router,
        {
            "HITLPause": "HITLPause",
            "ResearchAgent": "ResearchAgent",
            "DataAgent": "DataAgent",
            "DevTeam": "DevTeam",
            "FINISH": END,
            "END": END,
        },
    )

    workflow.add_conditional_edges(
        "HITLPause",
        pause_router,
        {
            "ResearchAgent": "ResearchAgent",
            "DataAgent": "DataAgent",
            "DevTeam": "DevTeam",
            "FINISH": END,
            "END": END,
        },
    )

    workflow.add_conditional_edges("ResearchAgent", worker_router)
    workflow.add_conditional_edges("DataAgent", worker_router)
    workflow.add_conditional_edges("DevTeam", worker_router)

    workflow.add_conditional_edges(
        "ErrorAnalyzer",
        error_router,
        {"SupervisorAgent": "SupervisorAgent", "JoinParallel": "JoinParallel"},
    )

    workflow.add_conditional_edges(
        "JoinParallel",
        join_router,
        {
            "SupervisorAgent": "SupervisorAgent",
            "ConsensusNode": "ConsensusNode",
            "__end__": END,
        },
    )

    workflow.add_conditional_edges("ConsensusNode", lambda x: "SupervisorAgent")

    # Compile with persistence
    memory = AsyncSqliteSaver.from_conn_string(DATABASE_STATE_PATH)
    workflow_app = workflow.compile(checkpointer=saver, interrupt_before=["HITLPause"])
    logger.info("graph_rebuilt_and_compiled")


# Setup Persistence
DATABASE_STATE_PATH = os.path.join(os.path.dirname(__file__), "data", "state.db")


class ModelConfigUpdate(BaseModel):
    provider: str
    tier: str
    model: str


class AgentModelUpdate(BaseModel):
    model_provider: Optional[str] = None
    model_tier: Optional[str] = None


class MCPServerConfig(BaseModel):
    name: str
    type: str  # toolbox, sse
    url: str
    auth_token: Optional[str] = None


class AgentCreate(BaseModel):
    name: str
    role: str
    system_prompt: str
    capabilities: List[str] = []
    model_provider: str = "google"
    model_tier: str = "fast"


class AgentUpdate(BaseModel):
    role: Optional[str] = None
    system_prompt: Optional[str] = None
    capabilities: Optional[List[str]] = None
    model_provider: Optional[str] = None
    model_tier: Optional[str] = None


class RunRequest(BaseModel):
    thread_id: str
    message: str
    thinking_mode: bool = False
    use_web: bool = True


class ThreadRenameRequest(BaseModel):
    name: str


@app.post("/run")
async def run_workflow(request: RunRequest):
    logger.info(
        "received_request", thread_id=request.thread_id, message=request.message
    )

    if not workflow_app:
        raise HTTPException(
            status_code=503, detail="Server is still initializing the graph..."
        )

    import json

    from fastapi.responses import StreamingResponse

    async def event_generator():
        config = {"configurable": {"thread_id": request.thread_id}}
        input_message = HumanMessage(content=request.message)

        try:
            current_agent = "SupervisorAgent"
            # Track content buffers per agent and last yielded content for delta streaming
            agent_buffers: Dict[str, str] = {}
            last_yielded_content: Dict[str, str] = {}

            async for event in workflow_app.astream_events(
                {
                    "messages": [input_message],
                    "plan": [],
                    "plan_step": 0,
                    "task_context": request.message,
                    "wait_count": 0,
                    "retry_data": {},
                    "intended_agent": "",
                    "require_consensus": False,
                    "thinking_mode": request.thinking_mode,
                    "use_web": request.use_web,
                },
                config,
                version="v2",
            ):
                kind = event["event"]
                # Extract agent name from metadata if available
                node_agent = event.get("metadata", {}).get("langgraph_node")

                # Blacklist of internal nodes that should NOT trigger UI updates or bubbles
                INTERNAL_NODES = [
                    "HITLGate",
                    "ErrorAnalyzer",
                    "JoinParallel",
                    "ConsensusNode",
                    "HITLPause",
                ]

                # Update current_agent ONLY if it's a new node start and NOT internal
                if kind == "on_chain_start" and node_agent:
                    current_agent = node_agent
                    if current_agent not in INTERNAL_NODES:
                        # Send an empty content signal so the UI knows this agent is now thinking
                        yield f"data: {json.dumps({'agent': current_agent})}\n\n"

                # Capture streaming tokens
                elif kind == "on_chat_model_stream":
                    # Use the agent name from the metadata of THIS specific stream event
                    stream_agent = event.get("metadata", {}).get(
                        "langgraph_node", current_agent
                    )

                    # If the stream is coming from an internal node, skip it
                    if stream_agent in INTERNAL_NODES:
                        continue

                    content = event["data"]["chunk"].content

                    if content:
                        # Initialize buffer for this agent if needed
                        if stream_agent not in agent_buffers:
                            agent_buffers[stream_agent] = ""
                            last_yielded_content[stream_agent] = ""

                        agent_buffers[stream_agent] += str(content)

                        # Check for __USER_RESPONSE__ prefix (tool-based user responses)
                        user_response_marker = "__USER_RESPONSE__:"
                        buffer = agent_buffers[stream_agent]

                        if user_response_marker in buffer:
                            # Extract content after the marker
                            start_idx = buffer.find(user_response_marker) + len(
                                user_response_marker
                            )
                            user_content = buffer[start_idx:]

                            # Only yield new content (delta since last yield)
                            if len(user_content) > len(
                                last_yielded_content[stream_agent]
                            ):
                                new_content = user_content[
                                    len(last_yielded_content[stream_agent]) :
                                ]
                                if new_content.strip():
                                    yield f"data: {json.dumps({'agent': stream_agent, 'content': new_content})}\n\n"
                                    last_yielded_content[stream_agent] = user_content
                        else:
                            # Direct streaming for better frontend consistency
                            if content:
                                # Apply filtering for a cleaner experience if it looks like a supervisor/plan message
                                # However, for direct tokens we usually can't filter easily without a buffer.
                                # The frontend usually handles the raw stream.
                                # But we can try a simple check if the token itself is a technical marker.
                                yield f"data: {json.dumps({'agent': stream_agent, 'content': str(content)})}\n\n"

                # Also capture tool message responses with __USER_RESPONSE__
                elif kind == "on_tool_end":
                    tool_output = event.get("data", {}).get("output", "")
                    if (
                        isinstance(tool_output, str)
                        and "__USER_RESPONSE__:" in tool_output
                    ):
                        # Extract agent from metadata
                        tool_agent = event.get("metadata", {}).get(
                            "langgraph_node", current_agent
                        )
                        # Extract the user-facing content
                        user_content = tool_output.split("__USER_RESPONSE__:", 1)[1]
                        if user_content.strip():
                            yield f"data: {json.dumps({'agent': tool_agent, 'content': user_content})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("workflow_failed", error=str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/approve")
async def approve_workflow(request: RunRequest):
    """
    Resumes a paused workflow.
    """
    logger.info("received_approval", thread_id=request.thread_id)
    config = {"configurable": {"thread_id": request.thread_id}}

    if not workflow_app:
        raise HTTPException(
            status_code=503, detail="Server is still initializing the graph..."
        )

    final_output = []

    try:
        # Resume by passing None (triggered by state update or just resume)
        # effectively continuing from the interruption.
        async for event in workflow_app.astream(None, config, stream_mode="values"):
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
async def get_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Returns aggregated performance metrics, optionally filtered by time."""
    return await usage_tracker.get_metrics(start_date, end_date)


@app.get("/metrics/history")
async def get_metrics_history(
    interval: str = Query("day", regex="^(minute|hour|day|week|month)$"),
    limit: int = 100,
    agent_name: Optional[str] = None,
    model_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Returns historical token usage grouped by interval, optionally filtered."""
    return await usage_tracker.get_usage_history(
        interval, limit, agent_name, model_name, start_date, end_date
    )


@app.get("/metrics/by-model")
async def get_metrics_by_model(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Returns token usage grouped by model, optionally filtered by time."""
    return await usage_tracker.get_token_usage_by_model(start_date, end_date)


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
    if not workflow_app:
        raise HTTPException(status_code=503, detail="Server initializing...")

    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = await workflow_app.aget_state(config)
        return {
            "values": snapshot.values,
            "next": snapshot.next,
            "metadata": snapshot.metadata,
        }
    except Exception as e:
        logger.error("get_state_failed", thread_id=thread_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/threads/{thread_id}/history")
async def get_thread_history(
    thread_id: str,
    limit: int = Query(
        default=20, ge=1, le=100, description="Number of messages to return"
    ),
    offset: int = Query(
        default=0, ge=0, description="Number of messages to skip from the end"
    ),
):
    """
    Retrieves a clean, user-facing conversation history from the LangGraph state.
    Filters out internal system messages and tool results.
    Supports pagination with limit and offset parameters.
    Returns messages in chronological order (oldest first within the returned batch).
    """
    if not workflow_app:
        raise HTTPException(status_code=503, detail="Server initializing...")

    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = await workflow_app.aget_state(config)
        messages = snapshot.values.get("messages", [])

        formatted = []
        if messages:
            for msg in messages:
                # Skip internal system messages or hidden context
                if isinstance(msg, SystemMessage):
                    continue

                # Skip ToolMessages (search results, code execution output) as they are for the model
                if isinstance(msg, ToolMessage):
                    continue

                # Map roles
                role = "user" if isinstance(msg, HumanMessage) else "assistant"

                # Extract content (handle complex block formats if any)
                content = msg.content
                if isinstance(content, list):
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and "text" in part:
                            text_parts.append(part["text"])
                        elif isinstance(part, str):
                            text_parts.append(part)
                    content = "\n".join(text_parts)

                # Filter Supervisor technical jargon using the same helper as streaming
                if role == "assistant":
                    # Use the shared helper function to ensure consistent filtering
                    content = filter_agent_content(str(content))

                # Skip messages with empty content
                if not str(content).strip():
                    continue

                # Extract agent name from various possible locations
                agent_name = None
                if role == "assistant":
                    # Try various sources for agent name
                    agent_name = getattr(msg, "name", None)
                    if not agent_name:
                        # Check response_metadata
                        meta = getattr(msg, "response_metadata", {})
                        agent_name = meta.get("agent_name") or meta.get(
                            "langgraph_node"
                        )
                    if not agent_name:
                        # Check additional_kwargs
                        kwargs = getattr(msg, "additional_kwargs", {})
                        agent_name = kwargs.get("agent_name") or kwargs.get(
                            "langgraph_node"
                        )
                    if not agent_name:
                        # Infer from content for Supervisor
                        if "SUMMARY:" in str(content) or "PLAN:" in str(content):
                            agent_name = "SupervisorAgent"
                        else:
                            agent_name = "Assistant"

                formatted.append(
                    {
                        "role": role,
                        "content": str(content),
                        "agent": agent_name,
                    }
                )

        # Apply pagination: get messages from the end, offset by 'offset', take 'limit' messages
        total_count = len(formatted)
        # Calculate start and end indices for pagination (from the end)
        end_idx = total_count - offset
        start_idx = max(0, end_idx - limit)

        paginated = formatted[start_idx:end_idx] if end_idx > 0 else []
        has_more = start_idx > 0  # There are older messages if start_idx > 0

        return {
            "messages": paginated,
            "hasMore": has_more,
            "total": total_count,
        }
    except Exception as e:
        logger.error("get_history_failed", thread_id=thread_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trajectories/recent")
async def get_recent_trajectories(limit: int = 10):
    """Returns the most recent trajectories (unique threads)."""
    return await usage_tracker.get_recent_trajectories(limit)


@app.get("/trajectories/{thread_id}")
async def get_trajectories(thread_id: str):
    """Returns execution history for a thread."""
    # Use DATABASE_STATE_PATH for trajectories
    async with aiosqlite.connect(DATABASE_STATE_PATH) as conn:
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


@app.patch("/trajectories/{thread_id}/name")
async def rename_thread(thread_id: str, request: ThreadRenameRequest):
    """Updates the custom name for a thread."""
    try:
        await usage_tracker.update_thread_name(thread_id, request.name)
        return {"status": "renamed", "thread_id": thread_id, "name": request.name}
    except Exception as e:
        logger.error("rename_failed", thread_id=thread_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents")
async def list_agents():
    """Returns metadata for all configured agents."""
    try:
        return await db_manager.get_all_agents()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/state/{thread_id}")
async def delete_state(thread_id: str):
    """Wipes state and checkpoints for a thread."""
    async with aiosqlite.connect(DATABASE_STATE_PATH) as conn:
        # Delete from LangGraph checkpointer tables
        await conn.execute("DELETE FROM checkpoints WHERE thread_id = ?", (thread_id,))
        await conn.execute("DELETE FROM writes WHERE thread_id = ?", (thread_id,))
        # Delete from our trajectories table
        await conn.execute("DELETE FROM trajectories WHERE thread_id = ?", (thread_id,))
        await conn.commit()
    return {"status": "deleted", "thread_id": thread_id}


@app.get("/memory/search")
async def search_memory(query: str = Query(...), k: int = 5):
    """Searches long-term vector memory."""
    if not researcher:
        raise HTTPException(status_code=503, detail="Agents initializing...")
    # DataAgent has the memory manager exposed or we can use the base special specialized ones
    # For simplicity, we use the Researcher's memory manager as it is standard
    results = researcher.memory.search_memory(query, k=k)
    return {"query": query, "results": results}


@app.get("/mcp/servers")
def list_mcp_servers():
    """Lists registered MCP servers and their status."""
    return mcp_router.servers


@app.post("/optimize/{agent_name}")
async def optimize_agent(agent_name: str):
    """Triggers prompt optimization for an agent based on failures."""
    new_prompt = await optimizer.optimize_agent(agent_name)
    if not new_prompt:
        return {"status": "no_improvement_needed", "agent": agent_name}

    optimizer.apply_optimization(agent_name, new_prompt)
    return {
        "status": "optimized",
        "agent": agent_name,
        "new_prompt_preview": new_prompt[:100] + "...",
    }


@app.get("/models/config")
def get_model_config():
    """Returns the current global tier-to-model mappings."""
    return model_router.tier_mappings


@app.post("/models/config")
async def update_model_config(update: ModelConfigUpdate):
    """Updates a global model mapping."""
    await model_router.update_mapping(update.provider, update.tier, update.model)
    return {"status": "updated", "config": model_router.tier_mappings}


@app.patch("/agents/{agent_name}/model")
async def update_agent_model(agent_name: str, update: AgentModelUpdate):
    """Updates a specific agent's model provider and tier in the database."""
    try:
        agents = await db_manager.get_all_agents()
        if agent_name not in agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

        agent_data = agents[agent_name]
        if update.model_provider:
            agent_data["model_provider"] = update.model_provider
        if update.model_tier:
            agent_data["model_tier"] = update.model_tier

        await db_manager.set_agent(agent_name, agent_data)
        return {"status": "updated", "agent": agent_name, "config": agent_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/secrets")
async def get_secrets_status():
    """Returns the status of known API keys (Set/Not Set). Values are masked."""
    secrets = await db_manager.get_all_secrets()
    keys = [
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "COHERE_API_KEY",
        "TAVILY_API_KEY",
        "OLLAMA_BASE_URL",
    ]
    status = {}
    for key in keys:
        val = secrets.get(key)
        if val:
            # Mask: show first 4 and last 2 characters
            masked = val[:4] + "..." + val[-2:] if len(val) > 6 else "****"
            status[key] = {"set": True, "value": masked}
        else:
            status[key] = {"set": False, "value": None}
    return status


@app.post("/config/secrets")
async def update_secrets(secrets: Dict[str, str]):
    """Updates one or more API keys and persists them to DB."""
    allowed_keys = [
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "COHERE_API_KEY",
        "TAVILY_API_KEY",
        "OLLAMA_BASE_URL",
    ]
    for key, val in secrets.items():
        if key not in allowed_keys:
            raise HTTPException(status_code=400, detail=f"Invalid secret key: {key}")
        await db_manager.set_secret(key, val)

    # Refresh model router cache
    await model_router.refresh_config()
    return {"status": "updated", "keys": list(secrets.keys())}


@app.post("/config/mcp")
async def add_mcp_server(config: MCPServerConfig):
    """Adds or updates an MCP server registry in the database."""
    server_data = config.model_dump()
    name = server_data.pop("name")
    await mcp_router.add_server(name, server_data)
    return {"status": "added", "server": name, "config": server_data}


@app.delete("/config/mcp/{server_name}")
async def delete_mcp_server(server_name: str):
    """Removes an MCP server registry from the database."""
    await mcp_router.delete_server(server_name)
    return {"status": "deleted", "server": server_name}


@app.get("/tools")
def list_all_tools():
    """Returns the complete catalog of registered tools."""
    return tool_registry.list_tools()


@app.post("/agents")
async def create_agent(agent: AgentCreate):
    """Creates a new agent and persists it to the database."""
    try:
        agents = await db_manager.get_all_agents()
        if agent.name in agents:
            raise HTTPException(
                status_code=400, detail=f"Agent {agent.name} already exists"
            )

        await db_manager.set_agent(agent.name, agent.model_dump())
        return {"status": "created", "agent": agent.name, "config": agent.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/agents/{agent_name}")
async def update_agent_config(agent_name: str, update: AgentUpdate):
    """Comprehensive update of an agent's configuration in the database."""
    try:
        agents = await db_manager.get_all_agents()
        if agent_name not in agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

        agent_data = agents[agent_name]
        update_dict = update.model_dump(exclude_unset=True)

        for key, value in update_dict.items():
            agent_data[key] = value

        await db_manager.set_agent(agent_name, agent_data)
        return {"status": "updated", "agent": agent_name, "config": agent_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/agents/{agent_name}")
async def delete_agent(agent_name: str):
    """Removes an agent from the database."""
    try:
        agents = await db_manager.get_all_agents()
        if agent_name not in agents:
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")

        await db_manager.delete_agent(agent_name)
        return {"status": "deleted", "agent": agent_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
