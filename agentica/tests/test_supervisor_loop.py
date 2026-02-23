import asyncio

from langchain_core.messages import AIMessage, HumanMessage
from src.core.config import refresh_agent_configs
from src.core.db_manager import db_manager
from src.core.supervisor import SupervisorAgent


async def test():
    await db_manager.initialize()
    await refresh_agent_configs()
    sup = SupervisorAgent()
    messages = [
        HumanMessage(content="What is the weather in Kathmandu?"),
        AIMessage(
            content="I'll search. NEXT AGENT: ResearchAgent", name="SupervisorAgent"
        ),
        AIMessage(content="It's 68F", name="ResearchAgent"),
    ]
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
    print("Supervisor Content:", res["messages"][0].content)


if __name__ == "__main__":
    asyncio.run(test())
