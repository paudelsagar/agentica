import json
import sys
import time
import uuid

import requests

BASE_URL = "http://localhost:8000"


def test_parallel_execution():
    print("Starting Parallel Execution Verification Test...")

    # We want to force the supervisor to choose multiple agents.
    # The prompt should be explicit.
    prompt = "I need you to do two things simultaneously: 1. Research the latest features of LangGraph. 2. Write a simple python script that prints 'Hello World'. Do these in parallel."

    thread_id = f"parallel-test-{str(uuid.uuid4())}"

    payload = {"thread_id": thread_id, "message": prompt}

    try:
        print(f"Sending request: {prompt} (Thread: {thread_id})")
        response = requests.post(f"{BASE_URL}/run", json=payload)
        response.raise_for_status()
        data = response.json()
        print("\n--- Response ---")
        print(json.dumps(data, indent=2))

        # Check if we need approval (HITL might trigger for Coder)
        while data.get("status") == "requires_action":
            print(f"\nWorkflow paused. Sending approval...")
            approve_payload = {"thread_id": thread_id, "message": "proceed"}
            response = requests.post(f"{BASE_URL}/approve", json=approve_payload)
            response.raise_for_status()
            data = response.json()
            print("\n--- Response (After Approval) ---")
            print(json.dumps(data, indent=2))

        print(
            "\nTest Completed. Please check server logs to verify 'ResearchAgent' and 'CoderAgent' were triggered."
        )

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        try:
            print(e.response.text)
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    test_parallel_execution()
