import glob
import importlib
import os
import sys
from typing import Callable, Dict, List

from langchain_core.tools import tool

from src.core.logger import get_logger

logger = get_logger(__name__)

DYNAMIC_TOOLS_DIR = os.path.join(os.getcwd(), "src", "tools", "dynamic")


class ToolManager:
    """
    Manages dynamic tool loading and reloading.
    """

    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        os.makedirs(DYNAMIC_TOOLS_DIR, exist_ok=True)
        # Ensure the directory is in sys.path so we can import modules from it
        if DYNAMIC_TOOLS_DIR not in sys.path:
            sys.path.append(DYNAMIC_TOOLS_DIR)

    def load_tools(self) -> List[Callable]:
        """
        Scans the dynamic tools directory and loads all valid tools.
        """
        self.tools = {}
        tool_files = glob.glob(os.path.join(DYNAMIC_TOOLS_DIR, "*.py"))

        logger.info(f"Scanning for dynamic tools in {DYNAMIC_TOOLS_DIR}...")

        for file_path in tool_files:
            module_name = os.path.basename(file_path).replace(".py", "")
            if module_name == "__init__":
                continue

            try:
                # Invalidate cache to allow hot-reloading
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    spec = importlib.util.spec_from_file_location(
                        module_name, file_path
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)

                        # Inspect module for functions with @tool decorator
                        # LangChain's @tool decorator adds a `is_langchain_tool` attribute (or similar identification)
                        # But simpler is to look for functions that are instances of StructuredTool or have specific attributes.
                        # Actually, better pattern: ask the module for a `get_tools()` function or similar convention.
                        # OR: just look for all callables that have `name` and `description` attributes if using @tool.

                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            # Check if it looks like a LangChain tool
                            if (
                                hasattr(attr, "name")
                                and hasattr(attr, "description")
                                and callable(attr)
                            ):
                                self.tools[attr.name] = attr
                                logger.info(f"Loaded dynamic tool: {attr.name}")

            except Exception as e:
                logger.error(f"Failed to load dynamic tool from {file_path}: {e}")

        logger.info(f"Total dynamic tools loaded: {len(self.tools)}")
        return list(self.tools.values())

    def refresh(self) -> List[Callable]:
        """
        Reloads all tools.
        """
        return self.load_tools()
