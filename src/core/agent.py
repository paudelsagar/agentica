import os
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
from langchain_core.tools import StructuredTool
from langchain_google_genai import ChatGoogleGenerativeAI

# Provider imports
from langchain_openai import ChatOpenAI
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from src.core.logger import get_logger

logger = get_logger(__name__)


class EnterpriseAgentConfig(BaseModel):
    name: str
    agent_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str
    capabilities: List[str] = []
    model_provider: str = "openai"  # openai, anthropic, google, xai
    model_name: str = "gpt-4o"
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

    def _get_llm(self):
        """Factory to create the LLM instance based on config."""
        provider = self.config.model_provider.lower()
        model = self.config.model_name

        if provider == "google":
            if not os.getenv("GOOGLE_API_KEY"):
                logger.warning("GOOGLE_API_KEY not found", agent=self.config.name)
            return ChatGoogleGenerativeAI(model=model, temperature=0)

        elif provider == "anthropic":
            if not os.getenv("ANTHROPIC_API_KEY"):
                logger.warning("ANTHROPIC_API_KEY not found", agent=self.config.name)
            return ChatAnthropic(model=model, temperature=0)

        elif provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                logger.warning("OPENAI_API_KEY not found", agent=self.config.name)
            return ChatOpenAI(model=model, temperature=0)

        elif provider == "xai":
            # xAI is compatible with OpenAI SDK
            if not os.getenv("XAI_API_KEY"):
                logger.warning("XAI_API_KEY not found", agent=self.config.name)
            return ChatOpenAI(
                model=model,
                api_key=os.getenv("XAI_API_KEY"),
                base_url="https://api.x.ai/v1",
                temperature=0,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def register_tool(self, name: str, func: Any):
        """Registers a tool with the internal FastMCP server and stores logical reference."""
        self.mcp_server.add_tool(func, name=name)
        self.tool_functions[name] = func

    def _get_langchain_tools(self) -> List[StructuredTool]:
        """Converts registered FastMCP tools to LangChain StructuredTools."""
        tools = []
        for name, func in self.tool_functions.items():
            # FastMCP decorators might wrap the function, but simpler to just use StructuredTool.from_function
            # provided the function has type hints and docstrings (which ours do).
            tools.append(StructuredTool.from_function(func, name=name))
        return tools

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Entry point for LangGraph node execution.
        """
        messages = state.get("messages", [])

        # 1. Bind tools
        tools = self._get_langchain_tools()
        self.log.info("binding_tools", tool_names=[t.name for t in tools])
        if tools:
            llm_with_tools = self.llm.bind_tools(tools)
        else:
            llm_with_tools = self.llm

        # 2. Add System Prompt if configured and not present
        if self.config.system_prompt:
            # Check if the first message is a SystemMessage, if not, prepend (conceptually)
            # For simpler graph state, we might just prepend it to the call
            messages = [SystemMessage(content=self.config.system_prompt)] + messages

        self.log.info("invoking_llm", provider=self.config.model_provider)

        # 3. Invoke LLM
        response = await llm_with_tools.ainvoke(messages)
        self.log.info(
            "llm_response",
            content=response.content,
            tool_calls=response.tool_calls,
            metadata=response.response_metadata,
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
                    # Execute python function directly
                    try:
                        result = self.tool_functions[tool_name](**tool_args)
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

        return {
            "messages": [response],
            "next_agent": "END",
        }
