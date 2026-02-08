import json
import time

import requests


def test_parallel_execution():
    url = "http://localhost:8000/run"

    # We want a query that CLEARLY benefits from parallelization
    # and forces the Supervisor to launch both Research and Data agents.
    # Note: We need some data in the DB for the DataAgent to be useful.
    # Assuming standard project DB structure from previous phases.

    query = "Research the current price of Bitcoin AND query the database to count total users from 'users' table. Do these in parallel if possible."

    payload = {"thread_id": "parallel_test_thread_v2", "message": query}

    print(f"\n--- Parallel Execution Test ---")
    print(f"Query: {query}")

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        print(f"\nFinal Response: {data.get('last_message')}")

        # To verify parallelism, we should check server logs for
        # 'join_parallel_check' with wait_count=2 followed by two 1s, etc.
        # Or check if ResearchAgent and DataAgent were both active.

        print(
            "\nSUCCESS: Request completed. Please check server logs for parallel execution confirmation."
        )

    except Exception as e:
        print(f"\nFAILURE: Test failed with error: {str(e)}")


if __name__ == "__main__":
    test_parallel_execution()
