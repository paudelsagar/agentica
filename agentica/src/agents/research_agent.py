import time
from typing import Optional

from src.core.agent import Agentica, AgenticaConfig
from src.core.config import load_agent_config
from src.core.logger import get_logger

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
#  Module-level Search Cache with TTL (5 minutes)                             #
# --------------------------------------------------------------------------- #

_search_cache: dict = {}  # {normalized_query: (timestamp, results_str)}
CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cached_result(query: str) -> Optional[str]:
    """Return cached search result if valid, else None."""
    key = query.strip().lower()
    if key in _search_cache:
        ts, result = _search_cache[key]
        if time.time() - ts < CACHE_TTL_SECONDS:
            return result
        else:
            del _search_cache[key]
    return None


def _set_cache(query: str, result: str):
    """Store search result in cache."""
    key = query.strip().lower()
    _search_cache[key] = (time.time(), result)


# --------------------------------------------------------------------------- #
#  Circuit Breaker — Fail fast after consecutive DDGS failures                #
# --------------------------------------------------------------------------- #

_circuit_failure_count = 0
_circuit_open_until = 0.0
CIRCUIT_BREAK_THRESHOLD = 3  # consecutive failures to trip
CIRCUIT_BREAK_COOLDOWN = 60  # seconds to wait before retrying


def _circuit_is_open() -> bool:
    """Check if circuit breaker is tripped."""
    return time.time() < _circuit_open_until


def _circuit_record_failure():
    """Record a DDGS failure, potentially tripping the breaker."""
    global _circuit_failure_count, _circuit_open_until
    _circuit_failure_count += 1
    if _circuit_failure_count >= CIRCUIT_BREAK_THRESHOLD:
        _circuit_open_until = time.time() + CIRCUIT_BREAK_COOLDOWN
        logger.warning(
            "circuit_breaker_tripped",
            failures=_circuit_failure_count,
            cooldown=CIRCUIT_BREAK_COOLDOWN,
        )


def _circuit_record_success():
    """Reset circuit breaker on success."""
    global _circuit_failure_count
    _circuit_failure_count = 0


class ResearchAgent(Agentica):
    """
    Specialized in searching the web and summarizing information.
    Features: TTL-based search caching, circuit breaker for DDGS.
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
            Performs a web search using DuckDuckGo.
            Features: caching, circuit breaker, relevance filtering.
            """
            self.log.info(f"web_search called: {query}")

            # 1. Check cache first
            cached = _get_cached_result(query)
            if cached:
                self.log.info("cache_hit", query=query)
                return cached

            # 2. Check circuit breaker
            if _circuit_is_open():
                self.log.warning("circuit_breaker_open_skipping_search")
                return "Search temporarily unavailable. Please try again shortly."

            import re

            def _is_relevant(results, q):
                """Only reject truly empty or unrelated results."""
                if not results:
                    return False

                q_lower = q.lower()
                stop_words = {
                    "what",
                    "who",
                    "when",
                    "where",
                    "why",
                    "how",
                    "the",
                    "and",
                    "for",
                    "with",
                    "are",
                    "is",
                    "of",
                    "in",
                    "to",
                    "about",
                    "does",
                    "can",
                    "current",
                    "today",
                    "now",
                }
                words = set(re.findall(r"\b[a-z]{3,}\b", q_lower)) - stop_words
                if not words:
                    return True

                # Specific intent boost: if query has 'temperature', 'weather', 'price', etc.
                intent_keywords = {
                    "temperature",
                    "weather",
                    "forecast",
                    "price",
                    "stock",
                    "vibe",
                    "status",
                    "live",
                }
                query_intents = words.intersection(intent_keywords)

                for r in results:  # Check all 5
                    text = (
                        r.get("body", "")
                        + " "
                        + r.get("title", "")
                        + " "
                        + r.get("snippet", "")
                    ).lower()

                    # Specific intent boost: if query has 'temperature', 'weather', 'price', etc.
                    if query_intents:
                        if any(intent in text for intent in query_intents):
                            return True

                    # Fuzzy match: if any of the core words match significantly
                    match_count = sum(1 for w in words if w in text)
                    if match_count >= (len(words) // 2) + 1:
                        return True

                    # Weather-site heuristic
                    if any(
                        w in q_lower for w in ["weather", "temperature", "forecast"]
                    ):
                        if any(
                            site in text
                            for site in [
                                "accuweather",
                                "timeanddate",
                                "weather.com",
                                "bbc",
                                "met office",
                                "weather-forecast",
                                "nws",
                            ]
                        ):
                            self.log.info(
                                f"relevance_boost_weather_site: true ({r.get('title')})"
                            )
                            return True

                self.log.info(f"relevance_check_failed for query: {q_lower}")
                return False

            def _safe_search(ddgs, q, method="text"):
                """Execute a DDGS search with error handling."""
                try:
                    if method == "text":
                        res = list(ddgs.text(q, max_results=5))
                    else:
                        res = list(ddgs.news(q, max_results=5))
                    return res if _is_relevant(res, q) else []
                except Exception as e:
                    self.log.warning(f"DDGS {method} search failed: {e}")
                    _circuit_record_failure()
                    return []

            # 3. Execute search
            results = []
            try:
                with DDGS() as ddgs:
                    results = _safe_search(ddgs, query, "text")
                    if not results:
                        self.log.info("text_empty_trying_news")
                        results = _safe_search(ddgs, query, "news")
            except Exception as e:
                self.log.error(f"DDGS failure: {e}")
                _circuit_record_failure()
                return f"Search engine error: {e}"

            if not results:
                return "No results found for this query."

            # Record success & format
            _circuit_record_success()

            lines = []
            for i, r in enumerate(results[:5]):
                title = r.get("title", "")
                snippet = r.get("body") or r.get("snippet", "")
                source = r.get("href") or r.get("link", "")
                lines.append(f"{i+1}. {title}\n   {snippet}\n   Source: {source}")
            result_str = f"Search results for '{query}':\n\n" + "\n\n".join(lines)

            # Cache the result
            _set_cache(query, result_str)
            return result_str

        def summarize(content: str) -> str:
            """Summarizes text content."""
            self.log.info(f"Summarizing content (first 50 chars): {content[:50]}...")
            return f"Summary: {content[:50]}..."

        def save_memory(text: str) -> str:
            """Saves important information to long-term memory."""
            return self.memory.add_memory(text)

        def recall_memory(query: str) -> str:
            """Searches long-term memory for relevant information."""
            results = self.memory.search_memory(query)
            if not results:
                return "No relevant memories found."
            return "\n\n".join(results)

        self.register_tool("web_search", web_search)
        self.register_tool("summarize", summarize)
        self.register_tool("save_memory", save_memory)
        self.register_tool("recall_memory", recall_memory)
