from typing import Any, Dict, List, Optional

from langchain_core.runnables import RunnableConfig

from src.core.agent import EnterpriseAgent
from src.core.config import load_agent_config

# MCP tool loading is now handled by the base class via MCPRouter


class DataAgent(EnterpriseAgent):
    """
    Data Agent that interacts with SQL databases via Google GenAI Toolbox.
    """

    def __init__(self):
        config = load_agent_config("DataAgent")
        super().__init__(config)
        self._tools_loaded = False

    async def _load_toolbox_tools(self):
        if self._tools_loaded:
            return

        try:
            await self.attach_mcp_server("Toolbox")
            self._tools_loaded = True

        except Exception as e:
            self.log.error("failed_to_load_toolbox_tools", error=str(e))

    async def __call__(
        self, state: Dict[str, Any], config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        # Ensure tools are loaded before invocation
        await self._load_toolbox_tools()
        return await super().__call__(state, config=config)
