import asyncio
import os

import aiosqlite
import yaml

from src.core.config import AGENTS_CONFIG_PATH
from src.core.prompt_optimizer import optimizer
from src.core.usage import usage_tracker


async def test_prompt_optimization():
    print("\n--- Phase 12: Automated Prompt Optimization Test ---")

    agent_name = "ResearchAgent"
    test_thread = "test_opt_123"

    # 1. Simulate negatives in the database
    print("\n1. Seeding failed trajectories...")
    await usage_tracker.initialize()
    async with aiosqlite.connect(usage_tracker.db_path) as db:
        # Failure 1: Agent hallucinates a tool
        await db.execute(
            "INSERT INTO trajectories (thread_id, agent_name, input, output, success, feedback) VALUES (?, ?, ?, ?, ?, ?)",
            (
                test_thread,
                agent_name,
                "Find the price of BTC",
                "I will use the secret_bitcoin_tool to find the price.",
                0,
                "Tool secret_bitcoin_tool not found.",
            ),
        )
        # Failure 2: Agent gives no citations
        await db.execute(
            "INSERT INTO trajectories (thread_id, agent_name, input, output, success, feedback) VALUES (?, ?, ?, ?, ?, ?)",
            (
                test_thread,
                agent_name,
                "Who is the CEO of Nvidia?",
                "Jensen Huang is the CEO. (No source provided)",
                1,
                "Please provide sources for your claims.",
            ),
        )
        await db.commit()

    print("SUCCESS: Failures seeded.")

    # 2. Run optimization (dry run)
    print(f"\n2. Running optimizer for {agent_name}...")
    new_prompt = await optimizer.optimize_agent(agent_name)

    if new_prompt:
        print("\n[OPTIMIZED PROMPT GENERATED]")
        print(new_prompt[:300] + "...")

        # Check for expected logical additions
        # We expect the optimizer to mention tool names or source citations
        keywords = ["sources", "tool", "bitcoin", "available"]
        found = [k for k in keywords if k.lower() in new_prompt.lower()]

        print(f"\nDetected keywords in new prompt: {found}")

        if len(found) >= 1:
            print(
                f"\nSUCCESS: Optimizer identified and addressed the failure patterns."
            )
        else:
            print("\nWARNING: Optimizer output may not be specific enough.")
    else:
        print("\nFAILURE: No optimized prompt generated.")

    # 3. Cleanup test data (optional but good practice)
    print("\n3. Cleaning up test data...")
    async with aiosqlite.connect(usage_tracker.db_path) as db:
        await db.execute("DELETE FROM trajectories WHERE thread_id = ?", (test_thread,))
        await db.commit()
    print("SUCCESS: Data cleaned.")


if __name__ == "__main__":
    asyncio.run(test_prompt_optimization())
