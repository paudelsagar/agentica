import asyncio
import os
from typing import Any, Dict, List, Optional

import aiosqlite
from src.core.db_manager import db_manager
from src.core.logger import get_logger
from src.core.model_router import model_router

logger = get_logger(__name__)


class PromptOptimizer:
    """
    Analyzes failed agent trajectories and optimizes system prompts (DSPy-style).
    """

    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            root_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            db_path = os.path.join(root_dir, "data", "state.db")
        self.db_path = db_path
        # Use a heavy model for optimization reasoning, initialized lazily
        self._optimizer_llm = None

    async def fetch_negatives(
        self, agent_name: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fetches trajectories that likely need improvement.
        Filter by explicit success=0 or keywords in output.
        """
        negatives = []
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Search for success=0 OR common error markers in output
            query = """
                SELECT * FROM trajectories 
                WHERE agent_name = ? 
                AND (
                    success = 0 
                    OR output LIKE '%Error Output:%' 
                    OR output LIKE '%REQUEST_CHANGES%'
                    OR output LIKE '%not found%'
                )
                ORDER BY timestamp DESC
                LIMIT ?
            """
            async with db.execute(query, (agent_name, limit)) as cursor:
                async for row in cursor:
                    negatives.append(dict(row))
        return negatives

    async def optimize_agent(self, agent_name: str) -> Optional[str]:
        """
        Analyzes negatives for an agent and returns a suggested system prompt.
        """
        negatives = await self.fetch_negatives(agent_name)
        if not negatives:
            logger.info("no_negatives_found_skipping_optimization", agent=agent_name)
            return None

        # Load current agent configuration from database
        try:
            agents = await db_manager.get_all_agents()
            if agent_name not in agents:
                logger.error("agent_not_found_for_optimization", agent=agent_name)
                return None
            agent_data = agents[agent_name]
        except Exception as e:
            logger.error("failed_to_fetch_agent_data_for_optimization", error=str(e))
            return None

        current_prompt = agent_data.get("system_prompt", "")

        # Format negatives for the optimizer LLM
        trajectory_str = ""
        for i, neg in enumerate(negatives):
            trajectory_str += f"\n--- Trajectory {i+1} ---\n"
            trajectory_str += f"INPUT: {neg['input']}\n"
            trajectory_str += f"OUTPUT: {neg['output']}\n"
            if neg["feedback"]:
                trajectory_str += f"FEEDBACK: {neg['feedback']}\n"

        optimization_instruction = f"""
You are a Meta-Prompt Engineer. Your goal is to analyze failures in an AI agent's performance and refine its SYSTEM PROMPT.

AGENT ROLE: {agent_data.get('role')}
CURRENT SYSTEM PROMPT:
{current_prompt}

I will provide you with several FAILED trajectories from this agent.
Analyze the patterns of failure (e.g., repeating mistakes, ignoring constraints, hallucinating tools).

FAILED TRAJECTORIES:
{trajectory_str}

TASK:
Rewrite the SYSTEM PROMPT to specifically address these failure modes without losing the original core instructions.
Add specific CONSTRAINTS, LOGICAL STEPS, or FEW-SHOT EXAMPLES to prevent these errors.
BE CONCISE but extremely effective.

OUTPUT FORMAT:
Return ONLY the new full system prompt. Do not include any explanation or markers.
"""
        logger.info("optimizing_prompt", agent=agent_name, count=len(negatives))

        from langchain_core.messages import HumanMessage

        if self._optimizer_llm is None:
            self._optimizer_llm = model_router.get_model(tier_or_name="heavy")

        response = await self._optimizer_llm.ainvoke(
            [HumanMessage(content=optimization_instruction)]
        )

        new_prompt = response.content.strip()
        return new_prompt

    async def apply_optimization(self, agent_name: str, new_prompt: str):
        """
        Updates the agent's system prompt in the database and refreshes the cache.
        """
        try:
            from src.core.config import refresh_agent_configs

            agents = await db_manager.get_all_agents()
            if agent_name not in agents:
                logger.error("agent_not_found_to_apply_optimization", agent=agent_name)
                return

            agent_data = agents[agent_name]
            agent_data["system_prompt"] = new_prompt

            await db_manager.set_agent(agent_name, agent_data)
            await refresh_agent_configs()

            logger.info("optimization_applied", agent=agent_name)
        except Exception as e:
            logger.error("failed_to_apply_optimization", error=str(e))


optimizer = PromptOptimizer()
