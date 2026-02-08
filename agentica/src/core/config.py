from typing import Any, Dict

from src.core.agent import Agentica, AgenticaConfig
from src.core.logger import get_logger

logger = get_logger(__name__)

AGENT_CONFIG_CACHE: Dict[str, AgenticaConfig] = {}


async def refresh_agent_configs():
    """Refreshes the global agent configuration cache from the database."""
    global AGENT_CONFIG_CACHE
    try:
        from src.core.db_manager import db_manager

        agents = await db_manager.get_all_agents()
        AGENT_CONFIG_CACHE = {
            name: AgenticaConfig(**config) for name, config in agents.items()
        }
        logger.info("agent_config_cache_refreshed", count=len(AGENT_CONFIG_CACHE))
    except Exception as e:
        logger.error("failed_to_refresh_agent_config_cache", error=str(e))


def load_agent_config(agent_name: str) -> AgenticaConfig:
    """
    Loads configuration for a specific agent from the cache.
    """
    if agent_name in AGENT_CONFIG_CACHE:
        return AGENT_CONFIG_CACHE[agent_name]

    raise ValueError(
        f"Configuration for agent '{agent_name}' not found. "
        "Please ensure the database is seeded and the server has refreshed the cache."
    )
