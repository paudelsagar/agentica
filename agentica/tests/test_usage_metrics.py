import os
import tempfile

import aiosqlite
import pytest
from src.core.usage import UsageTracker


@pytest.mark.asyncio
async def test_get_metrics_aggregation():
    # Use a temporary file for the SQLite database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        tracker = UsageTracker(db_path=db_path)
        await tracker.initialize()

        # Seed test data for multiple agents
        # ResearchAgent: 2 calls, 5000 total tokens, average latency 3000ms
        await tracker.record_usage("ResearchAgent", "t1", "m1", 1000, 1500, 2500, 2000)
        await tracker.record_usage("ResearchAgent", "t2", "m1", 1000, 1500, 2500, 4000)

        # CoderAgent: 1 call, 1000 total tokens, latency 1000ms
        await tracker.record_usage("CoderAgent", "t1", "m2", 400, 600, 1000, 1000)

        metrics = await tracker.get_metrics()

        assert "ResearchAgent" in metrics
        assert metrics["ResearchAgent"]["call_count"] == 2
        assert metrics["ResearchAgent"]["total_tokens"] == 5000
        assert metrics["ResearchAgent"]["avg_latency_ms"] == 3000.0

        assert "CoderAgent" in metrics
        assert metrics["CoderAgent"]["call_count"] == 1
        assert metrics["CoderAgent"]["total_tokens"] == 1000
        assert metrics["CoderAgent"]["avg_latency_ms"] == 1000.0

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.mark.asyncio
async def test_get_metrics_empty():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        tracker = UsageTracker(db_path=db_path)
        metrics = await tracker.get_metrics()
        assert metrics == {}

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
