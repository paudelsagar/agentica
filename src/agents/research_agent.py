from typing import Any, Dict

from src.core.agent import EnterpriseAgent
from src.core.config import load_agent_config
from src.core.memory import MemoryManager


class ResearchAgent(EnterpriseAgent):
    """
    Agent specialized in research tasks.
    """

    def __init__(self):
        config = load_agent_config("ResearchAgent")
        super().__init__(config)
        self.memory = MemoryManager()
        self._register_tools()

    def _register_tools(self):
        from langchain_community.tools import DuckDuckGoSearchRun

        # Search Tool
        try:
            search_tool = DuckDuckGoSearchRun()
        except:
            # Fallback if dependencies missing or network fails init?
            # But here we just init the class.
            search_tool = None

        @self.mcp_server.tool()
        def web_search(query: str) -> str:
            """
            Performs a web search using DuckDuckGo.
            """
            if not search_tool:
                return "Search tool unavailable."

            self.logger.info(f"Performing real web search for: {query}")
            try:
                return search_tool.invoke(query)
            except Exception as e:
                self.logger.error(f"Error in web_search: {e}")
                # Fallback to a mock response if real search fails (e.g. network issues in some envs)
                return f"Error in search engine: {e}"

        @self.mcp_server.tool()
        def summarize(content: str) -> str:
            """
            Summarizes text content.
            """
            self.logger.info(f"Summarizing content (first 50 chars): {content[:50]}...")
            return f"Summary: {content[:50]}..."

        @self.mcp_server.tool()
        def save_memory(text: str) -> str:
            """
            Saves important information to long-term memory.
            """
            return self.memory.add_memory(text)

        @self.mcp_server.tool()
        def recall_memory(query: str) -> str:
            """
            Searches long-term memory for relevant information.
            """
            results = self.memory.search_memory(query)
            if not results:
                return "No relevant memories found."
            return "\n\n".join(results)

        # Manually register tools for LangChain binding
        self.tool_functions["web_search"] = web_search
        self.tool_functions["summarize"] = summarize
        self.tool_functions["save_memory"] = save_memory
        self.tool_functions["recall_memory"] = recall_memory
