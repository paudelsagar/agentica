import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langchain_core.messages import HumanMessage
from src.agents.research_agent import ResearchAgent
from src.core.config import refresh_agent_configs
from src.core.db_manager import db_manager
from src.core.model_router import model_router


async def test_research_agent():
    print("Initializing...")
    await db_manager.initialize()
    await refresh_agent_configs()
    await model_router.refresh_config()

    agent = ResearchAgent()
    state = {
        "messages": [
            HumanMessage(content="what is the current weather of kathmandu nepal?")
        ],
        "plan": [],
        "plan_step": 0,
    }

    print("Calling ResearchAgent...")
    result = await agent(state)

    print("\n--- ResearchAgent Response ---")
    last_msg = result["messages"][-1]
    print(last_msg.content)


if __name__ == "__main__":
    asyncio.run(test_research_agent())
