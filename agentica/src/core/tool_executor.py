"""
ToolExecutor — Handles tool invocation with proper error boundaries and async support.
Extracted from the base Agentica agent class for clean separation of concerns.
"""

import asyncio
import inspect
from typing import Any, Callable, Dict, List

from langchain_core.messages import ToolMessage
from src.core.logger import get_logger

logger = get_logger(__name__)

# Per-tool timeout in seconds
TOOL_TIMEOUT = 30


class ToolExecutor:
    """
    Executes tool calls from LLM responses with:
    - Async support (wraps sync functions with asyncio.to_thread)
    - Per-tool timeouts
    - Typed error boundaries (network vs parsing vs generic)
    """

    def __init__(self, tool_functions: Dict[str, Callable], agent_name: str):
        self.tool_functions = tool_functions
        self.agent_name = agent_name
        self.log = logger.bind(agent_name=agent_name)

    async def execute_tool_calls(
        self, tool_calls: List[Dict[str, Any]]
    ) -> List[ToolMessage]:
        """
        Executes a list of tool calls and returns ToolMessages.
        Each tool is run with a timeout and proper error handling.
        """
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_call_id = tool_call["id"]

            if tool_name not in self.tool_functions:
                self.log.warning("tool_not_found", tool_name=tool_name)
                results.append(
                    ToolMessage(
                        content=f"Tool '{tool_name}' not found.",
                        tool_call_id=tool_call_id,
                        name=tool_name,
                    )
                )
                continue

            result = await self._execute_single_tool(tool_name, tool_args, tool_call_id)
            results.append(result)

        return results

    async def _execute_single_tool(
        self, name: str, args: Dict[str, Any], call_id: str
    ) -> ToolMessage:
        """Execute a single tool with timeout and error handling."""
        self.log.info("executing_tool", tool_name=name, args=args)
        func = self.tool_functions[name]

        try:
            result = await asyncio.wait_for(
                self._invoke_function(func, args),
                timeout=TOOL_TIMEOUT,
            )
            return ToolMessage(content=str(result), tool_call_id=call_id, name=name)

        except asyncio.TimeoutError:
            self.log.error("tool_timeout", tool_name=name)
            return ToolMessage(
                content=f"Error: Tool '{name}' timed out after {TOOL_TIMEOUT}s.",
                tool_call_id=call_id,
                name=name,
            )

        except ConnectionError as e:
            self.log.error("tool_network_error", tool_name=name, error=str(e))
            return ToolMessage(
                content=f"Network error: {str(e)[:100]}",
                tool_call_id=call_id,
                name=name,
            )

        except ValueError as e:
            self.log.error("tool_validation_error", tool_name=name, error=str(e))
            return ToolMessage(
                content=f"Invalid input: {str(e)[:100]}",
                tool_call_id=call_id,
                name=name,
            )

        except Exception as e:
            self.log.error("tool_execution_failed", tool_name=name, error=str(e))
            return ToolMessage(
                content=f"Error: {str(e)[:200]}",
                tool_call_id=call_id,
                name=name,
            )

    async def _invoke_function(self, func: Callable, args: Dict[str, Any]) -> Any:
        """
        Invokes a function, handling both sync and async variants.
        Sync functions are run in a thread pool to avoid blocking the event loop.
        """
        if inspect.iscoroutinefunction(func):
            return await func(**args)

        if hasattr(func, "__call__") and inspect.iscoroutinefunction(func.__call__):
            return await func(**args)

        # Sync function — run in thread pool to avoid blocking
        return await asyncio.to_thread(func, **args)
