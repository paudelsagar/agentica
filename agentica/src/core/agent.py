import os
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from src.core.logger import get_logger
from src.core.mcp import mcp_router
from src.core.memory import MemoryManager
from src.core.model_router import model_router
from src.core.registry import ToolEntry, tool_registry
from src.core.usage import load_monitor, usage_tracker

logger = get_logger(__name__)


class EnterpriseAgentConfig(BaseModel):
    model_config = {"extra": "allow"}

    name: str
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str
    capabilities: List[str] = []
    model_provider: str = "openai"  # openai, anthropic, google, xai
    model_tier: str = "heavy"
    system_prompt: Optional[str] = None


class EnterpriseAgent:
    """
    Base implementation of an Enterprise Agent.
    Uses FastMCP for tool management and LangGraph for orchestration.
    Integrates with LangChain Chat Models for decision making.
    """

    def __init__(self, config: EnterpriseAgentConfig):
        self.config = config
        # Initialize FastMCP server for tool definitions
        self.mcp_server = FastMCP(config.name)
        self.tool_functions: Dict[str, Callable] = {}
        self.llm = self._get_llm()
        self.log = logger.bind(agent_name=config.name, agent_id=config.agent_id)
        # Long-term memory
        self.memory = MemoryManager()

    async def _recall_context(self, messages: List[BaseMessage]) -> str:
        """
        Retrieves relevant semi-structured context from long-term memory.
        """
        if not messages:
            return ""

        # Use the last human message for semantic search
        last_human = next(
            (m.content for m in reversed(messages) if isinstance(m, HumanMessage)), ""
        )
        if not last_human:
            return ""

        self.log.info("proactive_memory_retrieval", query_preview=str(last_human)[:50])
        memories = self.memory.search_memory(str(last_human))
        if memories:
            context = "\n".join([f"- {m}" for m in memories])
            self.log.info("memory_context_found", context=context)
            return f"\n\n[IMPORTANT] RECALLED CONTEXT FROM LONG-TERM MEMORY (Use this to answer the user):\n{context}\n\n"
        return ""

    async def _reflect_and_store(
        self, messages: List[BaseMessage], response_content: str
    ):
        """
        Lightweight reflection to store important facts/lessons in memory.
        """
        if not messages:
            return

        # Find the last human message
        last_human = next(
            (m.content for m in reversed(messages) if isinstance(m, HumanMessage)), ""
        )

        # Only reflect if there was actual content to avoid noise
        if len(response_content) < 10 and not last_human:
            return

        # FILTER: Don't store if the response is basically an admission of ignorance or just routing
        content_upper = response_content.upper()
        ignorance_keywords = [
            "I DON'T KNOW",
            "I'M SORRY",
            "TROUBLE RECALLING",
            "CANNOT FIND",
        ]

        # If it's JUST routing noise (empty content before the headers)
        is_pure_routing = (
            "NEXT AGENT:" in content_upper
            and len(response_content.split("NEXT AGENT:")[0].strip()) < 20
        )

        if (
            any(kw in content_upper for kw in ignorance_keywords) or is_pure_routing
        ) and len(response_content) < 500:
            self.log.info(
                "skipping_reflection_as_noise", is_pure_routing=is_pure_routing
            )
            return

        self.log.info("automated_reflection_triggered")

        # Combine Human input + AI response for full context
        memory_text = f"Context: {last_human}\nFact learned during task '{self.config.name}': {response_content}"

        self.memory.add_memory(
            memory_text,
            metadata={"agent": self.config.name, "type": "automated_reflection"},
        )

    def _get_llm(self):
        """Factory to create the LLM instance based on config using ModelRouter."""
        return model_router.get_model(
            tier_or_name=self.config.model_tier,
            provider=self.config.model_provider,
            temperature=0,
        )

    def register_tool(self, name: str, func: Any):
        """Registers a tool with the internal FastMCP server and stores logical reference."""
        self.mcp_server.add_tool(func, name=name)
        self.tool_functions[name] = func

        # Register in global registry for discovery (Phase 16)
        description = (
            getattr(func, "__doc__", "") or f"Tool provided by {self.config.name}"
        )
        tool_registry.register_tool(
            ToolEntry(
                name=name, description=description.strip(), owner_agent=self.config.name
            )
        )

    def _get_langchain_tools(self) -> List[StructuredTool]:
        """Converts registered FastMCP tools to LangChain StructuredTools."""
        tools = []
        for name, func in self.tool_functions.items():
            # FastMCP decorators might wrap the function, but simpler to just use StructuredTool.from_function
            # provided the function has type hints and docstrings (which ours do).
            tools.append(StructuredTool.from_function(func, name=name))
        return tools

    async def attach_mcp_server(self, server_name: str):
        """
        Dynamically connects to an MCP server and registers its tools.
        """
        self.log.info("attaching_mcp_server", server=server_name)
        new_tools = await mcp_router.fetch_tools(server_name)

        for tool in new_tools:
            # Handle both function objects and complex tool objects
            name = getattr(
                tool, "_name", tool.__name__ if hasattr(tool, "__name__") else str(tool)
            )
            self.log.info("registering_dynamic_mcp_tool", name=name, server=server_name)
            self.register_tool(name, tool)

    async def _sanitize_history(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Sanitizes the message history to ensure the LLM only sees tool calls
        corresponding to tools it actually knows.

        Converts unknown tool calls/results into HumanMessages to preserve context
        without confusing the model's strict validation (e.g., Gemini).
        """
        sanitized = []
        invalid_ids = set()
        known_tools = set(self.tool_functions.keys())

        # 1. Basic tool sanitization
        temp_sanitized = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                temp_sanitized.append(msg)
            elif isinstance(msg, AIMessage) and msg.tool_calls:
                unknown = [tc for tc in msg.tool_calls if tc["name"] not in known_tools]
                if unknown:
                    for tc in unknown:
                        invalid_ids.add(tc["id"])
                    action_desc = (
                        f"[Agent Action: {', '.join(tc['name'] for tc in unknown)}]"
                    )
                    new_content = f"{msg.content}\n{action_desc}".strip()
                    temp_sanitized.append(HumanMessage(content=new_content))
                else:
                    temp_sanitized.append(msg)
            elif isinstance(msg, ToolMessage):
                if msg.tool_call_id in invalid_ids or (
                    msg.name and msg.name not in known_tools
                ):
                    temp_sanitized.append(
                        HumanMessage(content=f"[Agent Tool Result: {str(msg.content)}]")
                    )
                else:
                    temp_sanitized.append(msg)
            else:
                temp_sanitized.append(msg)

        # 2. Strict role alternation (especially for Gemini) and NO trailing AI message
        final_sanitized = []
        for msg in temp_sanitized:
            if not final_sanitized:
                final_sanitized.append(msg)
                continue

            last = final_sanitized[-1]
            # Merge consecutive messages of same type (simplified)
            if type(msg) == type(last) and not isinstance(msg, SystemMessage):
                if isinstance(msg, HumanMessage) or isinstance(msg, AIMessage):
                    last.content = f"{last.content}\n\n{msg.content}".strip()
                continue

            final_sanitized.append(msg)

        # 3. Ensure it doesn't end with an AIMessage
        if final_sanitized and isinstance(final_sanitized[-1], AIMessage):
            cmd = f"System: Proceed with the task as {self.config.role}."
            final_sanitized.append(HumanMessage(content=cmd))

        return final_sanitized

    async def __call__(
        self, state: Dict[str, Any], config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """
        Entry point for LangGraph node execution.
        """
        thread_id = (
            config.get("configurable", {}).get("thread_id", "unknown")
            if config
            else "unknown"
        )

        # 0. Cognitive Budget Check (Phase 15)
        await load_monitor.check_budget(thread_id)

        # 0.1 Predictive Scaling (Phase 19)
        current_llm = self.llm
        if self.config.model_tier == "fast":
            optimal_tier = await model_router.get_optimal_tier(
                self.config.name, self.config.model_provider
            )
            if optimal_tier == "heavy":
                self.log.info(
                    "predictive_scaling_upgrading_to_heavy", agent=self.config.name
                )
                current_llm = model_router.get_model(
                    tier_or_name="heavy",
                    provider=self.config.model_provider,
                    temperature=0,
                )

        messages = state.get("messages", [])

        # 1. History Trimming: Keep last 15 messages to prevent bloat
        if len(messages) > 15:
            self.log.info("trimming_history", original_count=len(messages), keeping=15)
            messages = messages[-15:]

        # 1. Proactive RAG: Recall context
        recalled_context = await self._recall_context(messages)

        # 2. Bind tools
        tools = self._get_langchain_tools()
        self.log.info("binding_tools", tool_names=[t.name for t in tools])
        if tools:
            llm_with_tools = current_llm.bind_tools(tools)
        else:
            llm_with_tools = current_llm

        # 3. Add System Prompt and Recalled Context
        # Filter out any existing SystemMessages to avoid conflicting instructions in hierachical flows
        messages = [m for m in messages if not isinstance(m, SystemMessage)]

        system_content = (self.config.system_prompt or "") + recalled_context
        if system_content:
            messages = [SystemMessage(content=system_content)] + messages

        self.log.info(
            "invoking_llm",
            provider=self.config.model_provider,
            message_count=len(messages),
        )

        # 4. Sanitize History for strict providers
        sanitized_messages = await self._sanitize_history(messages)

        # 5. Invoke LLM
        self.log.info(
            "sanitized_messages_summary",
            count=len(sanitized_messages),
            last_role=type(sanitized_messages[-1]).__name__,
        )
        start_time = time.perf_counter()
        response = await llm_with_tools.ainvoke(sanitized_messages, config=config)
        end_time = time.perf_counter()
        execution_time_ms = int((end_time - start_time) * 1000)

        # 6. Automated Reflection: Store info in memory
        await self._reflect_and_store(messages, response.content)

        # 7. Track Usage & Record Trajectory
        thread_id = (
            config.get("configurable", {}).get("thread_id", "unknown")
            if config
            else "unknown"
        )

        last_input = ""
        if messages:
            last_input = str(messages[-1].content)

        await usage_tracker.record_trajectory(
            thread_id=thread_id,
            agent_name=self.config.name,
            input_text=last_input,
            output_text=response.content,
            success=True,  # Default to true, optimizer will filter by feedback
            feedback="",
        )
        # Track Usage
        usage = getattr(response, "usage_metadata", {})

        if usage:
            # Try to get the literal model name from metadata for accurate cost tracking
            resolved_model = response.response_metadata.get("model_name") or getattr(
                self.llm,
                "model",
                getattr(self.llm, "model_name", self.config.model_tier),
            )

            await usage_tracker.record_usage(
                agent_name=self.config.name,
                thread_id=thread_id,
                model_name=resolved_model,
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                execution_time_ms=execution_time_ms,
            )

        self.log.info(
            "llm_response",
            content=response.content,
            tool_calls=response.tool_calls,
            metadata=response.response_metadata,
            usage=usage,
        )

        # 4. Handle Tool Calls
        if response.tool_calls:
            self.log.info("llm_requested_tools", count=len(response.tool_calls))
            # In a pure LangGraph React pattern, we might return the AIMessage and let a separate ToolNode handle it.
            # However, to keep our 'Agent Node' self-contained as per previous design, we will execute here.
            # OR we can just return the AIMessage and have the graph loop back?
            # For simplicity in this refactor, let's execute and return the result + AIMessage.

            # Actually, standard ReAct style in LangGraph usually splits Reason -> Act.
            # But let's support "Agent executes its own tools" for now to match interface.

            tool_messages = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]

                if tool_name in self.tool_functions:
                    self.log.info("executing_tool", tool_name=tool_name, args=tool_args)
                    # Execute tool function
                    try:
                        import inspect

                        func = self.tool_functions[tool_name]

                        if inspect.iscoroutinefunction(func) or inspect.isawaitable(
                            func
                        ):
                            result = await func(**tool_args)
                        elif hasattr(func, "__call__") and (
                            inspect.iscoroutinefunction(func.__call__)
                            or inspect.isawaitable(func.__call__)
                        ):
                            # This covers objects like ToolboxTool that have async __call__
                            # But wait, calling func() itself might return a coroutine
                            res = func(**tool_args)
                            if inspect.isawaitable(res):
                                result = await res
                            else:
                                result = res
                        else:
                            result = func(**tool_args)

                        tool_messages.append(
                            ToolMessage(
                                content=str(result),
                                tool_call_id=tool_call_id,
                                name=tool_name,
                            )
                        )

                    except Exception as e:
                        self.log.error(
                            "tool_execution_failed_exception",
                            tool_name=tool_name,
                            error=str(e),
                        )
                        import traceback

                        traceback.print_exc()
                        tool_messages.append(
                            ToolMessage(
                                content=f"Error: {str(e)}",
                                tool_call_id=tool_call_id,
                                name=tool_name,
                            )
                        )

                else:
                    self.log.warning("tool_not_found", tool_name=tool_name)
                    tool_messages.append(
                        ToolMessage(
                            content=f"Tool '{tool_name}' not found.",
                            tool_call_id=tool_call_id,
                            name=tool_name,
                        )
                    )

            # Append tool outputs to valid state
            # If we want to continue conversation, we might return these.
            # For this simple delegation flow, we might just recognize we are done or pass to next agent.

            # Recurse to self to process tool outputs
            return {
                "messages": [response] + tool_messages,
                "next_agent": self.config.name,
            }

        return {"messages": [response], "next_agent": "END", "wait_count": -1}
