from typing import Any, Dict, Optional

from src.core.agent import Agentica, AgenticaConfig
from src.core.config import load_agent_config


class ReviewerAgent(Agentica):
    """
    Reviews code for quality and security.
    """

    def __init__(self, config: Optional[AgenticaConfig] = None):
        if config is None:
            config = load_agent_config("ReviewerAgent")
        super().__init__(config)
        # ReviewerAgent primarily uses LLM knowledge, so no special tools needed initially.
        # It could potentially use a linter tool later.
