from typing import Any, Dict

from src.core.agent import EnterpriseAgent
from src.core.config import load_agent_config


class ReviewerAgent(EnterpriseAgent):
    """
    Agent specialized in reviewing code and providing feedback.
    """

    def __init__(self):
        config = load_agent_config("ReviewerAgent")
        super().__init__(config)
        # ReviewerAgent primarily uses LLM knowledge, so no special tools needed initially.
        # It could potentially use a linter tool later.
