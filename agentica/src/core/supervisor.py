import re
from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from src.core.agent import Agentica, AgenticaConfig
from src.core.config import load_agent_config
from src.core.consensus import Vote
from src.core.logger import get_logger
from src.core.model_router import model_router
from src.core.registry import tool_registry
from src.core.usage import usage_tracker

logger = get_logger(__name__)


class NextStep(BaseModel):
    next: List[
        Literal["ResearchAgent", "CoderAgent", "ReviewerAgent", "DataAgent", "FINISH"]
    ]


class SupervisorAgent(Agentica):
    """
    Orchestrates the workflow by deciding the next agent or step.
    """

    def __init__(self, config: Optional[AgenticaConfig] = None):
        """
        Supervisor Agent that orchestrates the workflow by deciding the next worker.
        """
        if config is None:
            config = load_agent_config("SupervisorAgent")
        super().__init__(config)

    async def __call__(
        self, state: Dict[str, Any], config: Optional[RunnableConfig] = None
    ) -> Dict[str, Any]:
        """
        Invokes the LLM to decide the next step, managing the multi-step plan.
        """
        messages = state.get("messages", [])
        plan = state.get("plan", [])
        plan_step = state.get("plan_step", 0)

        # 0. Prune history to avoid bias from previous failures (8B models are sensitive)
        if len(messages) > 6:
            # Keep the first (often the first human message) and the last 5
            messages = [messages[0]] + messages[-5:]
            self.log.info("pruned_supervisor_history", kept=len(messages))

        # 1. Proactive RAG: Recall context
        recalled_context = await self._recall_context(messages)

        # 2. Logic Guard: Force delegation for known real-time patterns
        # BREAK LOOP: Check for research results robustly
        has_research_results = False
        for m in messages:
            name = getattr(m, "name", "") or m.additional_kwargs.get("name", "")
            if name == "ResearchAgent":
                has_research_results = True
                break
            # Fallback check for content indicators if name is wiped
            content = str(m.content).upper()
            if "RESEARCHAGENT" in content and (
                "BASED ON MY SEARCH" in content or "FOUND THE FOLLOWING" in content
            ):
                has_research_results = True
                break

        # Check for dynamic needs (e.g., current events) using a simplified, generic guard
        # or completely omit static lists in favor of system prompt instructions.
        delegation_guard = ""
        use_web = state.get("use_web", True)
        if not has_research_results and use_web:
            # We add a subtle reminder, but leave the actual routing decision to the LLM
            delegation_guard = "\n\nCRITICAL THINKING: If the user requires real-time information, current facts, or external searches, you MUST delegate to ResearchAgent for the initial step. DO NOT attempt to answer questions about the world without searching first."
        elif not use_web:
            delegation_guard = "\n\nCRITICAL: Web search is currently DISABLED. DO NOT delegate to ResearchAgent. Use your internal knowledge only."

        # 3. Update System Prompt with plan, tools, and context
        all_tools = tool_registry.list_tools()
        if not use_web:
            all_tools = [t for t in all_tools if t.owner_agent != "ResearchAgent"]

        tools_str = "\n".join(
            [f"- {t.name} (Owner: {t.owner_agent}): {t.description}" for t in all_tools]
        )
        tool_discovery_prompt = (
            f"\n\nAVAILABLE TOOLS IN SYSTEM:\n{tools_str}" if all_tools else ""
        )
        self.log.info("discovered_tools", count=len(all_tools), tools=tools_str)

        consensus_instr = (
            "\n\nCRITICAL DECISIONS: If a step is high-risk (e.g., destructive actions), "
            "include 'CRITICAL' in your response to trigger a multi-agent consensus panel. "
            "You must then list multiple agents (e.g., 'NEXT AGENT: CoderAgent, ReviewerAgent'). "
            "Each agent in the panel MUST respond with 'DECISION: APPROVE' or 'DECISION: REJECT' "
            "and a 'REASON: <explanation>'."
        )

        plan_str = (
            "\n".join([f"{i+1}. {p}" for i, p in enumerate(plan)])
            if plan
            else "No plan yet."
        )
        context_prompt = f"\n\nCURRENT PLAN:\n{plan_str}\nCURRENT STEP: {plan_step + 1}"

        self.system_content = (
            (self.config.system_prompt or "")
            + tool_discovery_prompt
            + consensus_instr
            + context_prompt
            + recalled_context
            + delegation_guard
            + "\n\nCRITICAL: Your response MUST begin with a 'SUMMARY:' section "
            "intended for the user. Even if you are delegating, explain to the human "
            "what you are doing and why. NEVER leave the summary empty."
        )
        self.log.info(
            "consolidated_system_prompt", content_preview=self.system_content[:200]
        )
        # Filter out any existing SystemMessages to avoid redundant/conflicting instructions
        messages = [m for m in messages if not isinstance(m, SystemMessage)]

        system_msg = SystemMessage(content=self.system_content)
        messages = [system_msg] + messages

        self.log.info("supervisor_deciding_next_step", step=plan_step)

        # 3. Sanitize history for strict role alternation/trailing messages
        messages = await self._sanitize_history(messages)

        next_agent = ["FINISH"]
        wait_count = 0
        require_consensus = False

        # 3.1 Determine which LLM to use (check thinking mode)
        current_llm = self.llm
        if state.get("thinking_mode"):
            self.log.info("thinking_mode_enabled_switching_to_thinking_tier")
            current_llm = model_router.get_model(
                tier_or_name="thinking",
                provider=self.config.model_provider,
                temperature=0,
            )

        try:
            response = await current_llm.ainvoke(messages, config=config)
            response.name = self.config.name  # Set agent name for history
            content = response.content
            self.log.info("supervisor_raw_response", content=content)

            # 4. Multi-agent parsing (Moved UP)
            content_upper = content.upper()
            temp_next_agent = ["FINISH"]
            agent_matches = re.findall(r"NEXT AGENT:\s*(.*)", content, re.IGNORECASE)

            if agent_matches:
                parsed_agents = []
                for match in agent_matches:
                    targets_str = match.split("\n")[0].upper()
                    targets = [t.strip() for t in targets_str.split(",") if t.strip()]

                    for target in targets:
                        if "RESEARCH" in target:
                            parsed_agents.append("ResearchAgent")
                        elif "CODER" in target:
                            parsed_agents.append("CoderAgent")
                        elif "REVIEW" in target:
                            parsed_agents.append("ReviewerAgent")
                        elif "DATA" in target or "DATABASE" in target:
                            parsed_agents.append("DataAgent")
                        elif "DEVTEAM" in target or "DEVELOPMENT" in target:
                            parsed_agents.append("DevTeam")
                        elif "FINISH" in target:
                            parsed_agents.append("FINISH")

                if parsed_agents:
                    temp_next_agent = list(dict.fromkeys(parsed_agents))

            # If no match, fallback to simple lookup ONLY if we don't have results already
            has_research_results = any(
                getattr(m, "name", "") == "ResearchAgent" for m in messages
            )

            if temp_next_agent == ["FINISH"] and "FINISH" not in content_upper:
                if (
                    not has_research_results
                ):  # Prevent falling back into a loop if we already have the answer
                    if "RESEARCHAGENT" in content_upper:
                        temp_next_agent = ["ResearchAgent"]
                    elif "DATAAGENT" in content_upper:
                        temp_next_agent = ["DataAgent"]
                    elif "CODERAGENT" in content_upper:
                        temp_next_agent = ["CoderAgent"]
                    elif "REVIEWERAGENT" in content_upper:
                        temp_next_agent = ["ReviewerAgent"]

            # HARD LOOP PREVENTION: Force FINISH if we just got back from a worker
            # and the model is trying to re-delegate helplessly.
            if has_research_results:
                self.log.info(
                    "forcing_finish_to_prevent_loop", original=temp_next_agent
                )
                temp_next_agent = ["FINISH"]

            next_agent = temp_next_agent

            # 5. Extract parts: SUMMARY and Override
            summary_match = re.search(
                r"SUMMARY:(.*?)(?=\[END_SUMMARY\]|PLAN:|NEXT AGENT:|$)",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            summary = summary_match.group(1).strip() if summary_match else ""

            # If NEXT AGENT is present but no SUMMARY, use everything before NEXT AGENT
            if not summary and next_agent != ["FINISH"]:
                parts = re.split(r"NEXT AGENT:", content, flags=re.IGNORECASE)
                if len(parts) > 1 and len(parts[0].strip()) > 10:
                    summary = parts[0].strip()
                    # If the accidental summary contains refusal phrases, override it
                    if any(
                        kw in summary.lower()
                        for kw in ["unable", "cannot", "sorry", "nmda.gov.np"]
                    ):
                        summary = f"I am delegating to {', '.join(next_agent)} to fetch the information you requested."
                else:
                    summary = f"I am coordinating with {', '.join(next_agent)} to handle your request."

            # Final fallback for any refusal in ANY summary
            if any(
                kw in summary.lower()
                for kw in ["unable", "cannot", "sorry", "nmda.gov.np"]
            ) and next_agent != ["FINISH"]:
                summary = f"I've delegated the search to {', '.join(next_agent)} to get you the latest information."

            # 3. Automated Reflection: Store info in memory
            await self._reflect_and_store(messages, content)

            # Record Usage
            usage = getattr(response, "usage_metadata", {})
            thread_id = (
                config.get("configurable", {}).get("thread_id", "unknown")
                if config
                else "unknown"
            )
            if usage:
                resolved_model = response.response_metadata.get(
                    "model_name"
                ) or getattr(
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
                )

            # Extract Plan
            new_plan = []
            if "PLAN:" in content.upper():
                plan_match = re.search(
                    r"PLAN:(.*?)(?=NEXT AGENT:|$)", content, re.DOTALL | re.IGNORECASE
                )

                if plan_match:
                    steps = plan_match.group(1).strip().split("\n")
                    new_plan = [
                        re.sub(r"^\d+\.\s*", "", s).strip() for s in steps if s.strip()
                    ]
                    plan = new_plan
                    plan_step = 0  # reset if plan changed

                # Replaced by moved block
                elif "CODERAGENT" in content_upper:
                    next_agent = ["CoderAgent"]
                elif "REVIEWERAGENT" in content_upper:
                    next_agent = ["ReviewerAgent"]
                elif "DEVTEAM" in content_upper or "DEVELOPMENTTEAM" in content_upper:
                    next_agent = ["DevTeam"]
                elif "DATAAGENT" in content_upper:
                    next_agent = ["DataAgent"]

            # Use summary if available for the final message to user
            if summary:
                response.content = summary

            # 4. Critical Decision Check (Phase 17)
            require_consensus = "CRITICAL" in content_upper and len(next_agent) > 1

            # Increment plan step
            if next_agent != ["FINISH"]:
                plan_step += 1

            wait_count = len(next_agent) if next_agent != ["FINISH"] else 0

        except Exception as e:
            error_msg = str(e)
            self.log.error("supervisor_decision_failed", error=error_msg)
            response = AIMessage(content=f"Error: {error_msg}", name=self.config.name)
            next_agent = ["FINISH"]
            wait_count = 0

        # Record Trajectory
        thread_id = (
            config.get("configurable", {}).get("thread_id", "unknown")
            if config
            else "unknown"
        )
        last_input = ""
        if messages and len(messages) > 1:
            # message[0] is often system prompt we added above
            # the original messages were at the end of the list after our system prompt insertion
            # wait, messages = [system_msg] + messages (line 84)
            # so original last message is messages[-1]
            last_input = str(messages[-1].content)

        await usage_tracker.record_trajectory(
            thread_id=thread_id,
            agent_name=self.config.name,
            input_text=last_input,
            output_text=response.content,
            success=True if "Error:" not in response.content else False,
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
