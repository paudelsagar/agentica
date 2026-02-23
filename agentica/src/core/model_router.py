import os
import re
from typing import Any, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from src.core.logger import get_logger

logger = get_logger(__name__)

# Patterns that indicate simple queries (greetings, factual lookups)
SIMPLE_QUERY_PATTERNS = [
    r"^(hi|hello|hey|good morning|good evening|thanks|thank you)",
    r"^what (is|are|was|were)\b",
    r"^(who|when|where) (is|are|was|were)\b",
    r"^how (is|are|was|were)\b",
    r"\b(weather|temperature|time|date|price)\b",
]

# Patterns that indicate complex queries (multi-step, coding)
COMPLEX_QUERY_PATTERNS = [
    r"\b(implement|refactor|debug|fix|write code|build|create|design)\b",
    r"\b(analyze|compare|evaluate|explain in detail|step by step)\b",
    r"\b(python|javascript|typescript|sql|api|database)\b",
    r"\b(plan|strategy|architecture|workflow)\b",
]


class ModelRouter:
    """
    Manages dynamic LLM selection based on tiers (heavy, fast) or specific names.
    """

    def __init__(self):
        self.tier_mappings = {}
        self.secrets_cache = {}

    async def refresh_config(self):
        """Loads or reloads tier mappings and secrets from the database."""
        try:
            from src.core.db_manager import db_manager

            self.tier_mappings = await db_manager.get_model_mappings()
            self.secrets_cache = await db_manager.get_all_secrets()
            logger.info("model_router_config_loaded_from_db")
        except Exception as e:
            logger.error("failed_to_load_model_config_from_db", error=str(e))
            # Fallback to hardcoded defaults if critical
            self.tier_mappings = {
                "google": {
                    "heavy": "gemini-2.0-flash",
                    "fast": "gemini-2.0-flash",
                    "thinking": "gemini-2.0-flash-thinking-exp-01-21",
                }
            }

    async def update_mapping(self, provider: str, tier: str, model: str):
        """Updates a mapping and persists it to the database."""
        provider = provider.lower()
        tier = tier.lower()

        if provider not in self.tier_mappings:
            self.tier_mappings[provider] = {}

        self.tier_mappings[provider][tier] = model

        try:
            from src.core.db_manager import db_manager

            await db_manager.set_model_mapping(provider, tier, model)
            logger.info(
                "model_router_config_updated_in_db", provider=provider, tier=tier
            )
        except Exception as e:
            logger.error("failed_to_save_model_config_to_db", error=str(e))

    def get_model(
        self, tier_or_name: str, provider: str = "google", temperature: float = 0
    ):
        """
        Returns a ChatModel instance based on tier/name and provider.
        Includes automatic fallback if API keys are missing.
        """
        provider = provider.lower()
        tier_or_name = tier_or_name.lower()

        # Helper to check key availability
        def has_key(p: str):
            key_name = f"{p.upper()}_API_KEY"
            return bool(self.secrets_cache.get(key_name) or os.getenv(key_name))

        # Check if requested provider has a key, if not fallback
        if not has_key(provider):
            fallbacks = ["google", "openai", "anthropic", "xai"]
            found_fallback = False
            for fb in fallbacks:
                if fb != provider and has_key(fb):
                    logger.warning(
                        "provider_fallback_triggered",
                        requested=provider,
                        fallback=fb,
                        reason="missing_api_key",
                    )
                    provider = fb
                    found_fallback = True
                    break

            if not found_fallback:
                logger.error("no_api_keys_available", requested=provider)

        # Resolve tier to model name if possible
        model_name = tier_or_name
        if provider in self.tier_mappings:
            if tier_or_name in self.tier_mappings[provider]:
                model_name = self.tier_mappings[provider][tier_or_name]

        logger.info(
            "routing_model",
            provider=provider,
            requested=tier_or_name,
            resolved=model_name,
        )

        if provider == "google":
            return ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                convert_system_message_to_human=True,
            )
        elif provider == "openai":
            return ChatOpenAI(model=model_name, temperature=temperature)
        elif provider == "anthropic":
            return ChatAnthropic(model=model_name, temperature=temperature)
        elif provider == "xai":
            return ChatOpenAI(
                model=model_name,
                openai_api_key=self.secrets_cache.get("XAI_API_KEY")
                or os.getenv("XAI_API_KEY"),
                openai_api_base="https://api.x.ai/v1",
                temperature=temperature,
            )
        elif provider == "ollama":
            # Default to localhost:11434 if not specified
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            return ChatOllama(
                model=model_name,
                temperature=temperature,
                base_url=base_url,
                streaming=True,
            )

        raise ValueError(f"Unsupported provider: {provider}")

    async def get_optimal_tier(
        self, agent_name: str, provider: str = "google", db_path: Optional[str] = None
    ) -> str:
        """
        Dynamically selects the optimal tier based on historical performance.
        Defaults to 'fast'. If failure rate or high latency is detected on 'fast', promotes to 'heavy'.
        """
        if not db_path:
            # Default to root/data/state.db
            root_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            db_path = os.path.join(root_dir, "data", "state.db")

        if not os.path.exists(db_path):
            return "fast"

        try:
            import aiosqlite

            async with aiosqlite.connect(db_path) as db:
                # Check average latency for the 'fast' model of this provider
                fast_model = self.tier_mappings.get(provider, {}).get("fast", "fast")
                async with db.execute(
                    """
                    SELECT AVG(execution_time_ms) FROM token_usage 
                    WHERE agent_name = ? AND model_name LIKE ? 
                    ORDER BY id DESC LIMIT 5
                """,
                    (agent_name, f"%{fast_model}%"),
                ) as cursor:
                    row = await cursor.fetchone()
                    avg_latency = row[0] if row and row[0] else 0

                # Check success rate (success=1) in trajectories
                async with db.execute(
                    "SELECT SUM(success), COUNT(id) FROM trajectories WHERE agent_name = ? ORDER BY id DESC LIMIT 5",
                    (agent_name,),
                ) as cursor:
                    row = await cursor.fetchone()
                    success_count = row[0] if row and row[0] is not None else 5
                    total_count = row[1] if row and row[1] else 5

                # Heuristics for promotion to 'heavy':
                # 1. Average latency > 15 seconds
                # 2. Success rate below 80% (4 out of 5)
                success_rate = success_count / total_count if total_count > 0 else 1.0
                if avg_latency > 15000 or success_rate < 0.8:
                    logger.info(
                        "predictive_scaling_triggered",
                        agent=agent_name,
                        avg_latency=avg_latency,
                        success_rate=success_rate,
                    )
                    return "heavy"

        except Exception as e:
            logger.error("failed_to_calculate_optimal_tier", error=str(e))

        return "fast"

    def classify_query_complexity(self, query: str) -> str:
        """
        Classifies a query as 'simple' or 'complex' based on pattern matching.
        Returns 'simple' or 'complex'.
        """
        q = query.strip().lower()

        # Short queries are typically simple
        if len(q.split()) <= 5:
            return "simple"

        # Check for complex patterns first (higher priority)
        for pattern in COMPLEX_QUERY_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return "complex"

        # Check for simple patterns
        for pattern in SIMPLE_QUERY_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return "simple"

        # Default to fast for ambiguous queries
        return "simple"

    def get_cost_aware_tier(self, query: str, agent_name: str) -> str:
        """
        Returns the optimal model tier based on query complexity.
        Simple queries -> fast tier (cheaper, faster)
        Complex queries -> heavy tier (more capable)
        """
        complexity = self.classify_query_complexity(query)
        tier = "fast" if complexity == "simple" else "heavy"
        logger.info(
            "cost_aware_tier_selection",
            query_preview=query[:50],
            complexity=complexity,
            tier=tier,
            agent=agent_name,
        )
        return tier


model_router = ModelRouter()
