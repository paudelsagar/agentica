import json
import uuid

import requests

BASE_URL = "http://127.0.0.1:8000"


def run_test(test_name, query, expected_agent_hint=None):
    thread_id = str(uuid.uuid4())
    print(f"\n--- {test_name} (Thread: {thread_id}) ---")
    print(f"Query: {query}")

    payload = {"thread_id": thread_id, "message": query}

    try:
        response = requests.post(f"{BASE_URL}/run", json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Response: {data.get('last_message')}")

        # In a real test we would check the logs to see if the correct agent was invoked.
        # But for now, we just check if we got a sensible response.
        if expected_agent_hint and expected_agent_hint.lower() in str(data).lower():
            print("Likely SUCCESS (Hint found)")
        else:
            print("Check logs to confirm routing.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Test 1: Research
    run_test(
        "Test 1: Research Routing", "What is the current price of Ethereum?", "Ethereum"
    )

    # Test 2: Coding
    run_test(
        "Test 2: Coding Routing",
        "Write a python script to print 'Hello Supervisor' and execute it.",
        "Hello Supervisor",
    )
