from typing import Any, Dict, List, Optional

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

        self.servers = {}
        self._initialized = True

    async def refresh_config(self):
        """Loads or reloads server configurations from the database."""
        try:
            from src.core.db_manager import db_manager

            self.servers = await db_manager.get_mcp_servers()
            logger.info("mcp_config_loaded_from_db")
        except Exception as e:
            logger.error("failed_to_load_mcp_config_from_db", error=str(e))
            self.servers = {}

    async def add_server(self, name: str, config: Dict[str, Any]):
        """Adds or updates an MCP server configuration and persists it to DB."""
        self.servers[name] = config
        try:
            from src.core.db_manager import db_manager

            await db_manager.set_mcp_server(name, config)
            logger.info("mcp_server_added_to_db", name=name)
        except Exception as e:
            logger.error("failed_to_save_mcp_config_to_db", error=str(e))

    async def delete_server(self, name: str):
        """Removes an MCP server configuration and persists it to DB."""
        if name in self.servers:
            del self.servers[name]
            try:
                from src.core.db_manager import db_manager

                await db_manager.delete_mcp_server(name)
                logger.info("mcp_server_deleted_from_db", name=name)
            except Exception as e:
                logger.error("failed_to_delete_mcp_config_from_db", error=str(e))
        else:
            logger.warning("mcp_server_not_found_for_deletion", name=name)

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
