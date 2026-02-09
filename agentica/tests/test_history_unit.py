import asyncio
import os
import shutil
from datetime import datetime, timedelta

import pytest
from src.core.usage import UsageTracker

# Setup a temporary DB for testing
TEST_DB_PATH = "test_data/test_state.db"


@pytest.fixture
async def tracker():
    if os.path.exists("test_data"):
        shutil.rmtree("test_data")

    tracker = UsageTracker(db_path=TEST_DB_PATH)
    await tracker.initialize()
    yield tracker

    if os.path.exists("test_data"):
        shutil.rmtree("test_data")


@pytest.mark.asyncio
async def test_get_usage_history_day():
    tracker = UsageTracker(db_path=TEST_DB_PATH)
    await tracker.initialize()

    # Insert mock data
    # Today
    await tracker.record_usage("agent1", "t1", "gpt-4", 10, 10, 20)
    await tracker.record_usage("agent1", "t2", "gpt-4", 20, 20, 40)

    # Yesterday (manually via SQL to bypass current_timestamp default)
    import aiosqlite

    async with aiosqlite.connect(TEST_DB_PATH) as db:
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d 12:00:00")
        await db.execute(
            "INSERT INTO token_usage (total_tokens, timestamp) VALUES (?, ?)",
            (100, yesterday),
        )
        await db.commit()

    history = await tracker.get_usage_history(interval="day")

    # identifying today's date string
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    print(f"History: {history}")

    assert len(history) >= 2

    # Check if we have entries for today and yesterday
    today_entry = next((x for x in history if x["timestamp"] == today_str), None)
    yesterday_entry = next(
        (x for x in history if x["timestamp"] == yesterday_str), None
    )

    assert today_entry is not None
    assert today_entry["tokens"] == 60  # 20 + 40

    assert yesterday_entry is not None
    assert yesterday_entry["tokens"] == 100

    # Cleanup
    if os.path.exists("test_data"):
        shutil.rmtree("test_data")


if __name__ == "__main__":
    asyncio.run(test_get_usage_history_day())
