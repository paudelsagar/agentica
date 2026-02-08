from typing import Dict, List, Optional

from pydantic import BaseModel

from src.core.logger import get_logger

logger = get_logger(__name__)


class ToolEntry(BaseModel):
    name: str
    description: str
    owner_agent: str
    capabilities: List[str] = []


class ToolRegistry:
    """
    Central registry for all tools available in the Agentica ecosystem.
    Enables cross-team tool discovery.
    """

    def __init__(self):
        self.tools: Dict[str, ToolEntry] = {}

    def register_tool(self, entry: ToolEntry):
        """Registers a tool in the global registry."""
        self.tools[entry.name] = entry
        logger.info(
            "tool_registered_globally", tool=entry.name, owner=entry.owner_agent
        )

    def get_tool(self, name: str) -> Optional[ToolEntry]:
        """Retrieves a tool entry by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[ToolEntry]:
        """Lists all registered tools."""
        return list(self.tools.values())

    def find_tools_by_capability(self, capability: str) -> List[ToolEntry]:
        """Finds tools that match a specific capability or keyword."""
        results = []
        for tool in self.tools.values():
            if (
                capability.lower() in tool.description.lower()
                or capability in tool.capabilities
            ):
                results.append(tool)
        return results


# Global singleton
tool_registry = ToolRegistry()
