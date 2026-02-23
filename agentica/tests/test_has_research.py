import asyncio

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from src.core.config import refresh_agent_configs
from src.core.db_manager import db_manager
from src.core.supervisor import SupervisorAgent


async def test():
    await db_manager.initialize()
    await refresh_agent_configs()
    sup = SupervisorAgent()

    # Simulate the state after ResearchAgent ran once and returned a tool message and an AI message
    msg1 = HumanMessage(content="What is the weather in Kathmandu?")
    msg2 = AIMessage(content="I'll delegate to ResearchAgent.", name="SupervisorAgent")
    msg3 = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "web_search",
                "args": {"query": "weather kathmandu"},
                "id": "call_1",
            }
        ],
        name="ResearchAgent",
    )
    msg4 = ToolMessage(
        content="Some results.", tool_call_id="call_1", name="web_search"
    )
    msg5 = AIMessage(content="I didn't find the temperature.", name="ResearchAgent")

    messages = [msg1, msg2, msg3, msg4, msg5]

    # Verify has_research_results logic
    has_research_results = any(
        getattr(m, "name", "") == "ResearchAgent" for m in messages
    )
    print("has_research_results:", has_research_results)

    res = await sup(
        {
            "messages": messages,
            "next_agent": "SupervisorAgent",
            "task_status": "thinking",
            "plan": [],
            "plan_step": 0,
            "task_context": "",
            "intended_agent": "",
            "require_consensus": False,
            "wait_count": 0,
            "retry_data": {},
        },
        {"configurable": {"thread_id": "test_123"}},
    )
    print("Next Agent:", res["next_agent"])


if __name__ == "__main__":
    asyncio.run(test())
