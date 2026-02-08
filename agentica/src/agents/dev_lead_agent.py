import re
from typing import Any, Dict, Optional

from langchain_core.runnables import RunnableConfig

from src.core.agent import EnterpriseAgent
from src.core.config import load_agent_config


class DevLeadAgent(EnterpriseAgent):
    """
    Agent specialized in leading a development team and coordinating Coder/Reviewer.
    """

    def __init__(self):
        config = load_agent_config("DevLeadAgent")
        super().__init__(config)

    async def __call__(
        self, state: Dict[str, Any], config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        # Call base implementation to handle LLM invocation and usage
        result = await super().__call__(state, config)

        # Parse NEXT AGENT from response content
        last_message = result["messages"][-1].content
        next_agent = "FINISH"

        agent_match = re.search(r"NEXT AGENT:\s*(\w+)", last_message, re.IGNORECASE)
        if agent_match:
            target = agent_match.group(1).upper()
            if "CODER" in target:
                next_agent = "CoderAgent"
            elif "REVIEW" in target:
                next_agent = "ReviewerAgent"
            elif "FINISH" in target:
                next_agent = "FINISH"

        result["next_agent"] = next_agent
        return result
