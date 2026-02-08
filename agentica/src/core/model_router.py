import os
from typing import Any, Dict, Optional

from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

from src.core.logger import get_logger

logger = get_logger(__name__)


class ModelRouter:
    """
    Manages dynamic LLM selection based on tiers (heavy, fast) or specific names.
    """

    # Default mappings for Google (primary provider)
    TIER_MAPPINGS = {
        "google": {
            "heavy": "gemini-2.0-flash",  # "gemini-2.0-pro-exp-02-05" when stable, currently flash is very capable
            "fast": "gemini-2.0-flash",
        },
        "openai": {
            "heavy": "gpt-4o",
            "fast": "gpt-4o-mini",
        },
        "anthropic": {
            "heavy": "claude-3-5-sonnet-latest",
            "fast": "claude-3-haiku-20240307",
        },
        "xai": {
            "heavy": "grok-beta",
            "fast": "grok-beta",
        },
    }

    @staticmethod
    def get_model(tier_or_name: str, provider: str = "google", temperature: float = 0):
        """
        Returns a ChatModel instance based on tier/name and provider.
        """
        provider = provider.lower()
        tier_or_name = tier_or_name.lower()

        # Resolve tier to model name if possible
        model_name = tier_or_name
        if provider in ModelRouter.TIER_MAPPINGS:
            if tier_or_name in ModelRouter.TIER_MAPPINGS[provider]:
                model_name = ModelRouter.TIER_MAPPINGS[provider][tier_or_name]

        logger.info(
            "routing_model",
            provider=provider,
            requested=tier_or_name,
            resolved=model_name,
        )

        if provider == "google":
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                logger.warning("missing_google_api_key")
            return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)

        elif provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("missing_openai_api_key")
            return ChatOpenAI(model=model_name, temperature=temperature)

        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("missing_anthropic_api_key")
            return ChatAnthropic(model=model_name, temperature=temperature)

        elif provider == "xai":
            api_key = os.getenv("XAI_API_KEY")
            if not api_key:
                logger.warning("missing_xai_api_key")
            return ChatOpenAI(
                model=model_name,
                api_key=api_key,
                base_url="https://api.x.ai/v1",
                temperature=temperature,
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
                fast_model = self.TIER_MAPPINGS.get(provider, {}).get("fast", "fast")
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


model_router = ModelRouter()
