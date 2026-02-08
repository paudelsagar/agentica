import asyncio
import os
import traceback

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

from src.agents.research_agent import ResearchAgent

load_dotenv()


async def test_research():
    try:
        from langchain_community.tools import DuckDuckGoSearchRun

        print("Import successful")
        s = DuckDuckGoSearchRun()
        print("Init successful")
    except Exception as e:
        print("Init failed")
        traceback.print_exc()
        return

    agent = ResearchAgent()
    # Test tool directly
    search = agent.tool_functions["web_search"]
    print("Direct search test...")
    res = search("today gold price")
    print(f"Result: {res}")


if __name__ == "__main__":
    asyncio.run(test_research())
