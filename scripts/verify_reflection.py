import json
import sys
import time
import uuid

import requests

BASE_URL = "http://localhost:8000"


def run_test():
    thread_id = str(uuid.uuid4())
    print(f"Starting Reflection Verification Test (Thread ID: {thread_id})")

    # Request that requires coding
    payload = {
        "thread_id": thread_id,
        "message": "Write a python script to calculate the factorial of a number. Make sure to handle negative inputs.",
    }

    try:
        # Initial Request
        print(f"Sending request: {payload['message']}")
        response = requests.post(f"{BASE_URL}/run", json=payload)
        response.raise_for_status()
        data = response.json()

        print("\n--- Response 1 ---")
        print(json.dumps(data, indent=2))

        if data["status"] == "requires_action":
            print("\nWorkflow paused for approval (HITL). Approving...")
            approve_payload = {"thread_id": thread_id, "message": "approve"}
            response = requests.post(f"{BASE_URL}/approve", json=approve_payload)
            response.raise_for_status()
            data = response.json()
            print("\n--- Response 2 (After Approval) ---")
            print(json.dumps(data, indent=2))

        # We can't easily see the internal trace via the API return value alone,
        # as it only returns the last message.
        # However, if the ReviewerAgent ran, the final response might contain "APPROVE" or feedback.
        # Or better, we can check the server logs.
        # For this script, we just ensure it completes successfully and print the final output.
        # The user (me) will check the server logs for "ReviewerAgent".

        print("\nTest Completed. Check server logs for 'ReviewerAgent' activity.")

    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_test()
