import asyncio
import os

import aiosqlite


async def seed_data():
    db_path = "data/state.db"
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))

    async with aiosqlite.connect(db_path) as db:
        # Create table if not exists (safety)
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

        # Seed 5 high latency runs for ResearchAgent on gemini-2.0-flash
        # This should trigger promotion to 'heavy' for ResearchAgent
        for _ in range(5):
            await db.execute(
                "INSERT INTO token_usage (agent_name, thread_id, model_name, execution_time_ms) VALUES (?, ?, ?, ?)",
                (
                    "ResearchAgent",
                    "seed_thread",
                    "gemini-2.0-flash",
                    20000,
                ),  # 20s latency
            )
        await db.commit()
    print("Seeded Phase 19 test data.")


if __name__ == "__main__":
    asyncio.run(seed_data())
