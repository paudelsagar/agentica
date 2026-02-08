import os
from typing import Any, Dict, List, Optional

import yaml

from src.core.logger import get_logger

logger = get_logger(__name__)


class MCPRouter:
    """
    Registry and router for Model Context Protocol (MCP) servers.
    Allows agents to dynamically discover and connect to specialized toolsets.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPRouter, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.config_path = os.path.join(os.getcwd(), "src/config/mcp_servers.yaml")
        self.servers = self._load_config()
        self._initialized = True

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            logger.warning("mcp_servers_config_not_found", path=self.config_path)
            return {}

        try:
            with open(self.config_path, "r") as f:
                data = yaml.safe_load(f)
                return data.get("mcp_servers", {})
        except Exception as e:
            logger.error("failed_to_load_mcp_config", error=str(e))
            return {}

    async def fetch_tools(self, server_name: str) -> List[Any]:
        """
        Connects to an MCP server and retrieves available tools.
        """
        server_info = self.servers.get(server_name)
        if not server_info:
            logger.error("mcp_server_not_in_registry", name=server_name)
            return []

        server_type = server_info.get("type", "toolbox")
        url = server_info.get("url")

        logger.info("fetching_mcp_tools", server=server_name, type=server_type, url=url)

        try:
            if server_type == "toolbox":
                # Special handling for Google GenAI Toolbox
                from toolbox_core import ToolboxClient

                client = ToolboxClient(url=url)
                return await client.load_toolset()

            elif server_type == "sse":
                # Generic MCP SSE client (placeholder for future official SDK integration)
                # For now, we simulate or use a more generic client if possible
                logger.warning(
                    "mcp_sse_driver_not_fully_implemented", server=server_name
                )
                return []

            else:
                logger.error("unsupported_mcp_server_type", type=server_type)
                return []

        except Exception as e:
            logger.error("mcp_fetch_tools_failed", server=server_name, error=str(e))
            return []


# Global singleton
mcp_router = MCPRouter()
