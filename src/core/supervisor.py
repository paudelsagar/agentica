from typing import Any, Dict, Literal

from langchain_core.messages import SystemMessage
from pydantic import BaseModel

from src.core.agent import EnterpriseAgent
from src.core.config import load_agent_config


class NextStep(BaseModel):
    next: Literal["ResearchAgent", "CoderAgent", "FINISH"]


class SupervisorAgent(EnterpriseAgent):
    """
    Supervisor Agent that orchestrates the workflow by deciding the next worker.
    """

    def __init__(self):
        config = load_agent_config("SupervisorAgent")
        super().__init__(config)

    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invokes the LLM to decide the next step.
        """
        messages = state.get("messages", [])

        # Add System Prompt
        if self.config.system_prompt:
            messages = [SystemMessage(content=self.config.system_prompt)] + messages

        self.log.info("supervisor_deciding_next_step")

        # Use structured output to force a routing decision
        # Note: with_structured_output is supported by ChatGoogleGenerativeAI (Gemini)
        chain = self.llm.with_structured_output(NextStep)

        try:
            decision = await chain.ainvoke(messages)
            next_step = decision.next
        except Exception as e:
            self.log.error("supervisor_decision_failed", error=str(e))
            # Fallback or re-raise?
            # If supervisor fails, we should probably stop or default to something safe.
            # But let's log and default to FINISH to avoid loops if broken.
            next_step = "FINISH"

        self.log.info("supervisor_decision", next_agent=next_step)

        # We return the decision in the 'next_agent' key of the state
        # We do NOT return new messages, as the supervisor just routes.
        # Unless we want the supervisor to add a message? usually not necessary.
        return {"next_agent": next_step}
