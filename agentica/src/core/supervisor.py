import re
from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from src.core.agent import Agentica, AgenticaConfig
from src.core.config import load_agent_config
from src.core.consensus import Vote
from src.core.logger import get_logger
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

        # 1. Proactive RAG: Recall context
        recalled_context = await self._recall_context(messages)

        # 2. Update System Prompt with plan, tools, and context
        all_tools = tool_registry.list_tools()
        tools_str = "\n".join(
            [f"- {t.name} (Owner: {t.owner_agent}): {t.description}" for t in all_tools]
        )
        tool_discovery_prompt = (
            f"\n\nAVAILABLE TOOLS IN SYSTEM:\n{tools_str}" if all_tools else ""
        )

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

        system_content = (
            (self.config.system_prompt or "")
            + tool_discovery_prompt
            + consensus_instr
            + context_prompt
            + recalled_context
        )
        self.log.info(
            "consolidated_system_prompt", content_preview=system_content[:200]
        )
        system_msg = SystemMessage(content=system_content)
        messages = [system_msg] + messages

        self.log.info("supervisor_deciding_next_step", step=plan_step)
        next_agent = ["FINISH"]
        wait_count = 0
        require_consensus = False

        try:
            response = await self.llm.ainvoke(messages, config=config)
            response.name = self.config.name  # Set agent name for history
            content = response.content
            self.log.info("supervisor_raw_response", content=content)

            # 3. Extract parts: SUMMARY, PLAN, NEXT AGENT
            summary_match = re.search(
                r"SUMMARY:(.*?)(?=\[END_SUMMARY\]|PLAN:|$)",
                content,
                re.DOTALL | re.IGNORECASE,
            )
            summary = summary_match.group(1).strip() if summary_match else ""

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

            # Multi-agent parsing
            content_upper = content.upper()
            next_agent = ["FINISH"]
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
                    next_agent = list(dict.fromkeys(parsed_agents))  # Remove duplicates

            # If no match, fallback to simple lookup
            if next_agent == ["FINISH"] and "FINISH" not in content_upper:
                if "RESEARCHAGENT" in content_upper:
                    next_agent = ["ResearchAgent"]
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
