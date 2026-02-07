import os
from typing import Any, Dict

import yaml

from src.core.agent import EnterpriseAgentConfig
from src.core.logger import get_logger

logger = get_logger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/agents.yaml")


def load_agent_config(agent_name: str) -> EnterpriseAgentConfig:
    """
    Loads configuration for a specific agent from agents.yaml.
    """
    try:
        with open(CONFIG_PATH, "r") as f:
            config_data = yaml.safe_load(f)

        if "agents" not in config_data or agent_name not in config_data["agents"]:
            raise ValueError(
                f"Configuration for agent '{agent_name}' not found in {CONFIG_PATH}"
            )

        agent_data = config_data["agents"][agent_name]

        # Validate and return Pydantic model
        return EnterpriseAgentConfig(**agent_data)

    except FileNotFoundError:
        logger.error("config_file_not_found", path=CONFIG_PATH)
        raise
    except Exception as e:
        logger.error("config_load_failed", error=str(e))
        raise
