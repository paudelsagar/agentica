import asyncio
import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from src.agents.coder_agent import CoderAgent
from src.agents.research_agent import ResearchAgent
from src.core.graph import AgentState

# Load environment variables
load_dotenv()


async def main():
    print("Initializing Agentica System with LangGraph & LLMs...")

    # Instantiate Agents (Nodes)
    # They now use LLMs configured in their __init__
    researcher = ResearchAgent()
    coder = CoderAgent()

    # Build Graph
    workflow = StateGraph(AgentState)

    workflow.add_node("ResearchAgent", researcher)
    workflow.add_node("CoderAgent", coder)

    # Define Edges
    workflow.set_entry_point("ResearchAgent")

    # Conditional edge logic
    def router(state):
        return state.get("next_agent", END)

    workflow.add_conditional_edges(
        "ResearchAgent", router, {"CoderAgent": "CoderAgent", "END": END}
    )

    workflow.add_conditional_edges("CoderAgent", router, {"END": END})

    # Compile
    app = workflow.compile()

    # Run
    print("\n--- Starting Workflow ---")
    initial_state = {
        "messages": [
            HumanMessage(
                content="Use the web_search tool to find information about 'Agentic AI' and then ask the CoderAgent to write a summary script."
            )
        ]
    }

    async for output in app.astream(initial_state):
        for key, value in output.items():
            print(f"Output from Node '{key}':")
            print("---")
            # Create a shallow copy to avoid modifying the original dict during iteration
            safe_value = value.copy() if isinstance(value, dict) else value
            print(safe_value)
            print("\n")


if __name__ == "__main__":
    asyncio.run(main())
