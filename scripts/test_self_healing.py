import json
import time

import requests


def test_self_healing():
    url = "http://localhost:8000/run"

    # Query that forces CoderAgent to fail (deliberate bug)
    query = "Write a python script that intentionally has a syntax error (e.g., missing parenthesis) and try to execute it. Then fix it."

    payload = {"thread_id": "self_healing_test_thread", "message": query}

    print(f"\n--- Self-Healing & Retry Logic Test ---")
    print(f"Query: {query}")

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

        print(f"\nFinal Response: {data.get('last_message')}")

        print(
            "\nSUCCESS: Request completed. Please check server logs for 'error_detected_triggering_retry' to confirm self-healing worked."
        )

    except Exception as e:
        print(f"\nFAILURE: Test failed with error: {str(e)}")


if __name__ == "__main__":
    test_self_healing()
