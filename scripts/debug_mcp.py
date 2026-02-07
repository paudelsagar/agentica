import asyncio

from mcp.server.fastmcp import FastMCP


async def main():
    server = FastMCP("test")

    @server.tool()
    def test_tool() -> str:
        return "Hello"

    result = await server.call_tool("test_tool", arguments={})
    print(f"Type: {type(result)}")
    print(f"Value: {result}")


if __name__ == "__main__":
    asyncio.run(main())
