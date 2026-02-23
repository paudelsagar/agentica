from typing import Any, Dict, Optional

from src.core.agent import Agentica, AgenticaConfig
from src.core.config import load_agent_config
from src.core.memory import MemoryManager


class ResearchAgent(Agentica):
    """
    Specialized in searching the web and summarizing information.
    """

    def __init__(self, config: Optional[AgenticaConfig] = None):
        if config is None:
            config = load_agent_config("ResearchAgent")
        super().__init__(config)
        self._register_tools()

    def _register_tools(self):
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            self.log.error("duckduckgo_search_not_installed")

        def web_search(query: str) -> str:
            """
            Performs a web search with multi-layered fallbacks.
            """
            self.log.info(f"Performing layered web search for: {query}")

            def is_junk(results, q):
                if not results:
                    return True
                first_body = (
                    results[0].get("body", results[0].get("snippet", "")).lower()
                )
                first_title = results[0].get("title", "").lower()

                # Critical keywords that MUST be in the result if they are in the query
                critical_keywords = [
                    "kathmandu",
                    "nepal",
                    "weather",
                    "temperature",
                    "forecast",
                ]
                q_lower = q.lower()
                for kw in critical_keywords:
                    if kw in q_lower and (
                        kw not in first_body and kw not in first_title
                    ):
                        return True  # Missing a critical keyword from the query

                return False

            def do_search_text(ddgs, q):
                try:
                    res = list(ddgs.text(q, max_results=5))
                    return [] if is_junk(res, q) else res
                except Exception:
                    return []

            def do_search_news(ddgs, q):
                try:
                    res = list(ddgs.news(q, max_results=5))
                    return [] if is_junk(res, q) else res
                except Exception:
                    return []

            results = []
            try:
                with DDGS() as ddgs:
                    # Strategy 1: Primary Text Search
                    results = do_search_text(ddgs, query)

                    # Strategy 2: Weather-specific fallback (use News)
                    if not results and (
                        "weather" in query.lower() or "temperature" in query.lower()
                    ):
                        self.log.info(
                            "Primary text search failed for weather. Trying News..."
                        )
                        results = do_search_news(ddgs, query)

                    # Strategy 3: Query rephrasing fallback
                    if not results and "weather" in query.lower():
                        fallback = query.lower().replace(
                            "weather", "temperature report"
                        )
                        self.log.info(f"Trying rephrased fallback: {fallback}")
                        results = do_search_text(ddgs, fallback)

                    # Strategy 4: Broad News Search
                    if not results:
                        self.log.info("Still no results. Trying broad news search...")
                        results = do_search_news(ddgs, f"{query} report")
            except Exception as e:
                self.log.error(f"DDGS failure: {e}")
                return f"Search engine error: {e}"

            if not results:
                return "No reliable results found. Suggest trying keywords like 'temperature' or 'forecast'."

            formatted = []
            for r in results:
                formatted.append(
                    f"Title: {r.get('title')}\nSnippet: {r.get('body') or r.get('snippet')}\nSource: {r.get('href') or r.get('link')}"
                )
            return "\n\n".join(formatted)

        def summarize(content: str) -> str:
            """
            Summarizes text content.
            """
            self.log.info(f"Summarizing content (first 50 chars): {content[:50]}...")
            return f"Summary: {content[:50]}..."

        def save_memory(text: str) -> str:
            """
            Saves important information to long-term memory.
            """
            return self.memory.add_memory(text)

        def recall_memory(query: str) -> str:
            """
            Searches long-term memory for relevant information.
            """
            results = self.memory.search_memory(query)
            if not results:
                return "No relevant memories found."
            return "\n\n".join(results)

        # Register tools globally and for LangChain binding
        self.register_tool("web_search", web_search)
        self.register_tool("summarize", summarize)
        self.register_tool("save_memory", save_memory)
        self.register_tool("recall_memory", recall_memory)
