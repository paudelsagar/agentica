import os
from datetime import datetime
from typing import Any, Dict, Optional

import aiosqlite

from src.core.logger import get_logger

logger = get_logger(__name__)


class UsageTracker:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            # Default to root/data/state.db
            root_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            db_path = os.path.join(root_dir, "data", "state.db")
        self.db_path = db_path
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return

        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT,
                    thread_id TEXT,
                    model_name TEXT,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    total_tokens INTEGER,
                    execution_time_ms INTEGER DEFAULT 0,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            # Migration: Add column if it doesn't exist (safety)
            try:
                await db.execute(
                    "ALTER TABLE token_usage ADD COLUMN execution_time_ms INTEGER DEFAULT 0"
                )
                await db.commit()
            except:
                pass

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS trajectories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT,
                    agent_name TEXT,
                    input TEXT,
                    output TEXT,
                    success INTEGER,
                    feedback TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            await db.commit()
        self._initialized = True

    async def record_usage(
        self,
        agent_name: str,
        thread_id: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        execution_time_ms: int = 0,
    ):
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO token_usage (agent_name, thread_id, model_name, prompt_tokens, completion_tokens, total_tokens, execution_time_ms)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        agent_name,
                        thread_id,
                        model_name,
                        prompt_tokens,
                        completion_tokens,
                        total_tokens,
                        execution_time_ms,
                    ),
                )
                await db.commit()
            logger.info(
                "recorded_token_usage",
                agent=agent_name,
                thread_id=thread_id,
                total_tokens=total_tokens,
                execution_time_ms=execution_time_ms,
            )
        except Exception as e:
            logger.error("failed_to_record_usage", error=str(e))

    async def record_trajectory(
        self,
        thread_id: str,
        agent_name: str,
        input_text: str,
        output_text: str,
        success: bool = True,
        feedback: str = "",
    ):
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO trajectories (thread_id, agent_name, input, output, success, feedback)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        thread_id,
                        agent_name,
                        input_text,
                        output_text,
                        1 if success else 0,
                        feedback,
                    ),
                )
                await db.commit()
            logger.info(
                "recorded_trajectory",
                agent=agent_name,
                thread_id=thread_id,
                success=success,
            )
        except Exception as e:
            logger.error("failed_to_record_trajectory", error=str(e))

    async def get_total_usage(self, thread_id: str) -> int:
        """
        Calculates total token usage for a specific thread.
        """
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT SUM(total_tokens) FROM token_usage WHERE thread_id = ?",
                    (thread_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row and row[0] else 0
        except Exception as e:
            logger.error("failed_to_get_usage", error=str(e))
            return 0

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Returns aggregated performance metrics per agent.
        """
        try:
            await self.initialize()
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    """
                    SELECT 
                        agent_name, 
                        COUNT(*) as call_count,
                        SUM(total_tokens) as total_tokens,
                        AVG(execution_time_ms) as avg_latency_ms
                    FROM token_usage 
                    GROUP BY agent_name
                    """
                ) as cursor:
                    rows = await cursor.fetchall()
                    metrics = {}
                    for row in rows:
                        metrics[row[0]] = {
                            "call_count": row[1],
                            "total_tokens": row[2],
                            "avg_latency_ms": round(row[3], 2) if row[3] else 0,
                        }
                    return metrics
        except Exception as e:
            logger.error("failed_to_get_metrics", error=str(e))
            return {}


class LoadMonitor:
    """
    Monitors cognitive load (token usage) and enforces budgets.
    """

    def __init__(self, tracker: UsageTracker, budget: int = 1000000):
        self.tracker = tracker
        self.budget = budget

    async def check_budget(self, thread_id: str):
        """
        Checks if the current thread is within its cognitive budget.
        Raises an error if the budget is exceeded.
        """
        total = await self.tracker.get_total_usage(thread_id)
        if total > self.budget:
            logger.error(
                "cognitive_budget_exceeded",
                thread_id=thread_id,
                total=total,
                limit=self.budget,
            )
            raise RuntimeError(
                f"Cognitive budget exceeded for thread '{thread_id}'. "
                f"Usage: {total} tokens, Limit: {self.budget} tokens."
            )

        logger.info(
            "budget_check_passed",
            thread_id=thread_id,
            current_usage=total,
            budget=self.budget,
        )


# Global singletons
usage_tracker = UsageTracker()
load_monitor = LoadMonitor(usage_tracker)
