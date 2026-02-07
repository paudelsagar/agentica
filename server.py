import os
from typing import Any, Dict, List

import aiosqlite
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel

from src.agents.coder_agent import CoderAgent
from src.agents.research_agent import ResearchAgent
from src.core.graph import AgentState
from src.core.logger import configure_logger, get_logger
from src.core.supervisor import SupervisorAgent

# Load environment variables
load_dotenv(dotenv_path=".env")

# Configure logging
configure_logger()
logger = get_logger(__name__)

app = FastAPI(title="Agentic AI Enterprise Server")

# Initialize Agents
supervisor = SupervisorAgent()
researcher = ResearchAgent()
coder = CoderAgent()

# Build Graph
workflow = StateGraph(AgentState)
workflow.add_node("SupervisorAgent", supervisor)
workflow.add_node("ResearchAgent", researcher)
workflow.add_node("CoderAgent", coder)

workflow.set_entry_point("SupervisorAgent")


def router(state):
    # Retrieve the next agent from the state
    next_agent = state.get("next_agent", "FINISH")

    # If the Supervisor decides "FINISH", we return that.
    # If a worker finishes (returns "END" in next_agent), we route back to Supervisor.
    return next_agent


# Supervisor Edges
workflow.add_conditional_edges(
    "SupervisorAgent",
    router,
    {"ResearchAgent": "ResearchAgent", "CoderAgent": "CoderAgent", "FINISH": END},
)

# Worker Edges
# If worker returns "END" (done), go back to Supervisor.
# If worker returns its own name (tool use), loop back to itself.
workflow.add_conditional_edges(
    "ResearchAgent",
    router,
    {"ResearchAgent": "ResearchAgent", "END": "SupervisorAgent"},
)
workflow.add_conditional_edges(
    "CoderAgent",
    router,
    {"CoderAgent": "CoderAgent", "END": "SupervisorAgent"},
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
            # We must compile the graph with the checkpointer
            # Note: compiling per request is not ideal for performance but necessary if checkpointer depends on conn context
            # OR we can manage a global connection pool. For simplicity here:
            # Compile with interrupt
            app_graph = workflow.compile(
                checkpointer=checkpointer, interrupt_before=["CoderAgent"]
            )

            async for event in app_graph.astream(
                {"messages": [input_message]}, config, stream_mode="values"
            ):
                if "messages" in event:
                    final_output = event["messages"]
    except Exception as e:
        logger.error("workflow_failed", error=str(e))
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
                last_response = (
                    f"Workflow paused. Waiting for approval to run: {snapshot.next}"
                )
    except Exception:
        pass

    # Extract the last AIMessage content for response
    if status == "success" and final_output:
        last_msg = final_output[-1]
        if hasattr(last_msg, "content"):
            last_response = last_msg.content

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

    last_response = "Processing completed."
    if final_output:
        last_msg = final_output[-1]
        if hasattr(last_msg, "content"):
            last_response = last_msg.content

    return {
        "thread_id": request.thread_id,
        "status": "success",
        "last_message": last_response,
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}
