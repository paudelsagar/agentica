import asyncio
import os
from typing import Any, Dict, List, Optional

import aiosqlite
import yaml

from src.core.config import AGENTS_CONFIG_PATH
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
        # Use a heavy model for optimization reasoning
        self.optimizer_llm = model_router.get_model(tier_or_name="heavy")

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

        # Load current prompt
        with open(AGENTS_CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)

        current_prompt = config["agents"][agent_name].get("system_prompt", "")

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

AGENT ROLE: {config['agents'][agent_name].get('role')}
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

        response = await self.optimizer_llm.ainvoke(
            [HumanMessage(content=optimization_instruction)]
        )

        new_prompt = response.content.strip()
        return new_prompt

    def apply_optimization(self, agent_name: str, new_prompt: str):
        """
        Updates agents.yaml with the new prompt.
        """
        with open(AGENTS_CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f)

        config["agents"][agent_name]["system_prompt"] = new_prompt

        with open(AGENTS_CONFIG_PATH, "w") as f:
            yaml.dump(config, f, sort_keys=False)

        logger.info("optimization_applied", agent=agent_name)


optimizer = PromptOptimizer()
