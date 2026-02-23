import asyncio

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


async def test():
    # Let's see if AIMessage name is preserved when serialized / dumped by pydantic
    m = AIMessage(content="test")
    m.name = "ResearchAgent"

    # Simulate pydantic serialization which LangChain/LangGraph does
    d = m.dict()
    print("Serialization dict:", d)
    print("Message name:", m.name)


if __name__ == "__main__":
    asyncio.run(test())
