import asyncio
from collections import defaultdict
from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field
from src.core.agent import Agentica, AgenticaConfig
from src.core.config import load_agent_config
from src.core.logger import get_logger
from src.core.model_router import model_router
from src.core.registry import tool_registry
from src.core.usage import usage_tracker

logger = get_logger(__name__)

# --------------------------------------------------------------------------- #
#  Structured Output Models — replaces fragile regex parsing                   #
# --------------------------------------------------------------------------- #

VALID_AGENTS = Literal[
    "ResearchAgent", "CoderAgent", "ReviewerAgent", "DataAgent", "DevTeam", "FINISH"
]

AGENT_CAPABILITIES = {
    "DataAgent": {
        "description": "Database specialist with direct SQL access via MCP Toolbox. Handles ALL questions about internal/structured data.",
        "triggers": [
            "database",
            "data",
            "query",
            "sql",
            "users",
            "user",
            "accounts",
            "account",
            "merchants",
            "merchant",
            "transactions",
            "transaction",
            "payment",
            "kyc",
            "list",
            "show",
            "get",
            "find",
            "report",
            "balance",
            "volume",
            "summary",
            "pending",
            "active",
            "failed",
            "verified",
            "p2p",
            "currency",
            "daily",
            "recent",
            "travel",
        ],
        "tools": "MCP Toolbox for Databases (users, accounts, merchants, transactions, KYC, currency, reporting)",
    },
    "ResearchAgent": {
        "description": "Web researcher with DuckDuckGo search. Handles questions requiring real-time info from the internet.",
        "triggers": [
            "search",
            "web",
            "internet",
            "news",
            "weather",
            "price",
            "stock",
            "current",
            "latest",
            "trending",
            "what is",
            "who is",
            "how to",
            "wikipedia",
            "article",
            "blog",
            "website",
        ],
        "tools": "web_search, summarize, save_memory, recall_memory",
    },
    "DevTeam": {
        "description": "Development team (CoderAgent + ReviewerAgent + DevLead). Handles code writing, debugging, and review.",
        "triggers": [
            "code",
            "implement",
            "build",
            "develop",
            "fix",
            "debug",
            "write code",
            "refactor",
            "program",
            "script",
            "function",
            "class",
            "api",
            "endpoint",
            "test",
            "review code",
        ],
        "tools": "write_code, execute_code, review_code",
    },
}


class RouterDecision(BaseModel):
    """Structured routing decision from the Supervisor LLM."""

    summary: str = Field(
        description="A concise, user-facing explanation of what is happening and why. "
        "This is shown directly to the user."
    )
    next_agents: List[VALID_AGENTS] = Field(
        default=["FINISH"],
        description="List of agents to delegate to next, or ['FINISH'] if the task is complete.",
    )
    plan: List[str] = Field(
        default_factory=list,
        description="Optional multi-step plan. Each item is one step.",
    )


class SupervisorAgent(Agentica):
    """
    Orchestrates the workflow by deciding the next agent or step.
    Uses structured output for deterministic routing decisions.
    """

    AGENT_TIMEOUT = 30  # seconds

    def __init__(self, config: Optional[AgenticaConfig] = None):
        if config is None:
            config = load_agent_config("SupervisorAgent")
        super().__init__(config)

    # ------------------------------------------------------------------ #
    #  Prompt Construction — extracted for clarity                        #
    # ------------------------------------------------------------------ #

    def _classify_intent(self, query: str) -> Optional[str]:
        """
        Keyword-based pre-classification to assist LLM routing.
        Returns the best-matching agent name, or None if ambiguous.
        """
        query_lower = query.lower()
        scores = {}
        for agent_name, caps in AGENT_CAPABILITIES.items():
            score = sum(1 for t in caps["triggers"] if t in query_lower)
            if score > 0:
                scores[agent_name] = score

        if not scores:
            return None

        # Return top match only if it has >= 2 keyword hits
        best_agent = max(scores, key=scores.get)
        if scores[best_agent] >= 2:
            self.log.info(
                "intent_classified",
                query=query[:50],
                agent=best_agent,
                score=scores[best_agent],
            )
            return best_agent
        return None

    def _build_system_prompt(
        self,
        state: Dict[str, Any],
        plan: List[str],
        plan_step: int,
        recalled_context: str,
        has_research_results: bool,
    ) -> str:
        """Builds a system prompt with agent capability awareness and routing hints."""
        use_web = state.get("use_web", True)
        task_context = state.get("task_context", "")

        # Agent capability registry (always included)
        caps_lines = []
        for agent_name, caps in AGENT_CAPABILITIES.items():
            if not use_web and agent_name == "ResearchAgent":
                continue
            caps_lines.append(
                f"- {agent_name}: {caps['description']}\n  Tools: {caps['tools']}"
            )
        caps_section = "\n\nAVAILABLE AGENTS:\n" + "\n".join(caps_lines)

        # Tool discovery — grouped by agent for clear routing context
        all_tools = tool_registry.list_tools()
        if not use_web:
            all_tools = [t for t in all_tools if t.owner_agent != "ResearchAgent"]
        tools_by_agent = defaultdict(list)
        for t in all_tools:
            tools_by_agent[t.owner_agent].append(t.name)
        tools_section = ""
        if tools_by_agent:
            tools_str = "\n".join(
                f"- {agent}: {', '.join(tools)}"
                for agent, tools in tools_by_agent.items()
            )
            tools_section = f"\n\nREGISTERED TOOLS BY AGENT:\n{tools_str}"

        # Plan context
        plan_section = ""
        if plan:
            plan_str = "\n".join(f"{i + 1}. {p}" for i, p in enumerate(plan))
            plan_section = (
                f"\n\nCURRENT PLAN:\n{plan_str}\nCURRENT STEP: {plan_step + 1}"
            )

        # Delegation guard
        delegation_guard = ""
        if has_research_results:
            delegation_guard = (
                "\n\nCRITICAL: ResearchAgent has already provided information. "
                "Do NOT delegate back to ResearchAgent unless you need totally different facts. "
                "Instead, your SUMMARY should now provide the final answer to the user based on the tool results."
            )
        elif use_web:
            delegation_guard = (
                "\n\nCRITICAL: If the user needs real-time information, current facts, "
                "or web searches, delegate to ResearchAgent. Do NOT answer from memory."
            )
        elif not use_web:
            delegation_guard = "\n\nCRITICAL: Web search is DISABLED. Do NOT delegate to ResearchAgent."

        # Intent classification routing hint
        routing_hint = ""
        hint_agent = self._classify_intent(task_context)
        if hint_agent:
            routing_hint = (
                f"\n\nROUTING HINT: This query strongly matches {hint_agent}'s capabilities. "
                f"Delegate to {hint_agent} unless you have a specific reason not to."
            )

        base_prompt = self.config.system_prompt or ""
        return (
            f"{base_prompt}{caps_section}{tools_section}{plan_section}"
            f"{recalled_context}{delegation_guard}{routing_hint}"
        )

    def _check_research_results(self, messages: List) -> bool:
        """
        Check if ResearchAgent has already contributed results FOR THE CURRENT QUERY.
        We only look at messages since the last HumanMessage.
        """
        # Find index of last human message
        last_human_idx = -1
        for i in range(len(messages) - 1, -1, -1):
            if isinstance(messages[i], HumanMessage):
                last_human_idx = i
                break

        if last_human_idx == -1:
            return False

        # Check if ResearchAgent spoke AFTER that human message
        for m in messages[last_human_idx + 1 :]:
            name = getattr(m, "name", "") or m.additional_kwargs.get("name", "")
            if name == "ResearchAgent":
                return True
        return False

    # ------------------------------------------------------------------ #
    #  Decision Parsing — structured output with fallback                #
    # ------------------------------------------------------------------ #

    async def _get_structured_decision(
        self, llm, messages: List, config: Optional[RunnableConfig]
    ) -> RouterDecision:
        """
        Attempts structured output first. If it fails (e.g., Ollama returns free text),
        parses the error's embedded free-text response directly — no second LLM call needed.
        """
        try:
            structured_llm = llm.with_structured_output(RouterDecision)
            decision = await asyncio.wait_for(
                structured_llm.ainvoke(messages, config=config),
                timeout=self.AGENT_TIMEOUT,
            )
            self.log.info("structured_routing_success", decision=decision.model_dump())
            return decision
        except asyncio.TimeoutError:
            self.log.error("supervisor_timeout")
            return RouterDecision(
                summary="I'm taking longer than expected. Please try again.",
                next_agents=["FINISH"],
            )
        except Exception as e:
            error_text = str(e)
            self.log.warning(
                "structured_output_failed_parsing_error_text", error=error_text[:200]
            )
            # The error message from langchain contains the raw LLM output — parse it directly
            return self._parse_free_text(error_text)

    def _parse_free_text(self, content: str) -> RouterDecision:
        """Parse routing decision from free-text LLM output (no LLM call needed)."""
        import re

        content_upper = content.upper()

        # Parse agents
        next_agents: List[str] = []
        agent_map = {
            "RESEARCHAGENT": "ResearchAgent",
            "CODERAGENT": "CoderAgent",
            "REVIEWERAGENT": "ReviewerAgent",
            "DATAAGENT": "DataAgent",
            "DEVTEAM": "DevTeam",
        }
        for keyword, agent_name in agent_map.items():
            if keyword in content_upper:
                next_agents.append(agent_name)

        # Also check "NEXT AGENT:" pattern
        agent_matches = re.findall(r"NEXT AGENT:\s*(.*)", content, re.IGNORECASE)
        if agent_matches:
            for match in agent_matches:
                target = match.split("\n")[0].upper().strip()
                if "RESEARCH" in target:
                    next_agents.append("ResearchAgent")
                elif "CODER" in target:
                    next_agents.append("CoderAgent")
                elif "DATA" in target:
                    next_agents.append("DataAgent")
                elif "FINISH" in target:
                    next_agents.append("FINISH")

        # Deduplicate
        next_agents = list(dict.fromkeys(next_agents)) if next_agents else ["FINISH"]

        # Parse summary
        summary = ""
        summary_match = re.search(
            r"SUMMARY:\s*(.*?)(?=\n\s*NEXT AGENT:|PLAN:|$)",
            content,
            re.DOTALL | re.IGNORECASE,
        )
        if summary_match:
            summary = summary_match.group(1).strip()

        if not summary and next_agents != ["FINISH"]:
            summary = f"Delegating to {', '.join(next_agents)} to handle your request."

        if not summary:
            summary = "Processing your request."

        # Parse plan
        plan = []
        if "PLAN:" in content_upper:
            plan_match = re.search(
                r"PLAN:(.*?)(?=NEXT AGENT:|$)",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            if plan_match:
                steps = plan_match.group(1).strip().split("\n")
                plan = [re.sub(r"^\d+\.\s*", "", s).strip() for s in steps if s.strip()]

        return RouterDecision(
            summary=summary,
            next_agents=next_agents,
            plan=plan,
        )

    # ------------------------------------------------------------------ #
    #  Main Entry Point                                                   #
    # ------------------------------------------------------------------ #

    async def __call__(
        self, state: Dict[str, Any], config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """Invokes the LLM to decide the next step."""
        messages = state.get("messages", [])
        plan = state.get("plan", [])
        plan_step = state.get("plan_step", 0)

        # 0. Prune history (keep first + last 5)
        if len(messages) > 6:
            messages = [messages[0]] + messages[-5:]
            self.log.info("pruned_supervisor_history", kept=len(messages))

        # 1. Context recall (skip on initial delegation)
        has_prior_agent_work = any(
            getattr(m, "name", "") and getattr(m, "name", "") != self.config.name
            for m in messages
            if not isinstance(m, (SystemMessage, HumanMessage))
        )
        recalled_context = ""
        if has_prior_agent_work:
            recalled_context = await self._recall_context(messages)

        # 2. Check for existing research results
        has_research_results = self._check_research_results(messages)

        # 3. Build system prompt
        system_content = self._build_system_prompt(
            state, plan, plan_step, recalled_context, has_research_results
        )

        # 4. Prepare messages
        messages = [m for m in messages if not isinstance(m, SystemMessage)]
        messages = [SystemMessage(content=system_content)] + messages
        messages = await self._sanitize_history(messages)

        self.log.info("supervisor_deciding_next_step", step=plan_step)

        # 5. Select LLM
        current_llm = self.llm
        if state.get("thinking_mode"):
            self.log.info("thinking_mode_enabled")
            current_llm = model_router.get_model(
                tier_or_name="thinking",
                provider=self.config.model_provider,
                temperature=0,
            )

        # 6. Get structured decision
        decision = await self._get_structured_decision(current_llm, messages, config)

        # 7. Apply loop prevention
        next_agent = list(decision.next_agents)
        if has_research_results and "ResearchAgent" in next_agent:
            # Only allow a second research if the first one was absolutely empty
            # For now, let's be strict and force a finish.
            self.log.info(
                "forcing_finish_to_prevent_research_loop", original=next_agent
            )
            next_agent = ["FINISH"]
        elif has_research_results and "FINISH" not in next_agent:
            # If we had results and the LLM is wandering to other specialists, maybe restrict?
            # For now, allow other specialists but keep an eye.
            pass

        # 8. Update plan
        if decision.plan:
            plan = decision.plan
            plan_step = 0

        # 9. Build response
        summary = decision.summary
        if not summary and next_agent != ["FINISH"]:
            summary = (
                f"Coordinating with {', '.join(next_agent)} to handle your request."
            )

        response = AIMessage(content=summary, name=self.config.name)

        # 10. Increment plan step
        if next_agent != ["FINISH"]:
            plan_step += 1

        wait_count = len(next_agent) if next_agent != ["FINISH"] else 0
        require_consensus = len(next_agent) > 1 and next_agent != ["FINISH"]

        # 11. Record usage & trajectory
        thread_id = (
            config.get("configurable", {}).get("thread_id", "unknown")
            if config
            else "unknown"
        )

        last_input = str(messages[-1].content) if messages else ""
        await usage_tracker.record_trajectory(
            thread_id=thread_id,
            agent_name=self.config.name,
            input_text=last_input,
            output_text=response.content,
            success="Error:" not in response.content,
            feedback=response.content if "Error:" in response.content else "",
        )

        self.log.info(
            "supervisor_decision",
            next_agent=next_agent,
            plan_step=plan_step,
            wait_count=wait_count,
        )
        return {
            "next_agent": next_agent,
            "plan": plan,
            "plan_step": plan_step,
            "messages": [response],
            "wait_count": wait_count,
            "require_consensus": require_consensus,
        }
