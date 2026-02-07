import time
import uuid

import requests

BASE_URL = "http://127.0.0.1:8000"


def run_test():
    thread_id = str(uuid.uuid4())
    print(f"\n--- HITL Test (Thread: {thread_id}) ---")

    # 1. Trigger CoderAgent
    print("1. Sending request to trigger CoderAgent...")
    payload = {
        "thread_id": thread_id,
        "message": "Write a python script 'hitl_test.py' that prints 'Approved!' and execute it.",
    }

    try:
        response = requests.post(f"{BASE_URL}/run", json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Response: {data.get('last_message')}")

        if data.get("status") == "requires_action":
            print("SUCCESS: Workflow paused as expected.")
        else:
            print("FAILURE: Workflow did not pause.")
            return

    except Exception as e:
        print(f"Error triggering workflow: {e}")
        return

    # 2. Approve
    print("\n2. Sending Approval...")
    time.sleep(2)

    try:
        response = requests.post(f"{BASE_URL}/approve", json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Response: {data.get('last_message')}")

        if (
            "Approved!" in str(data)
            or "executed" in str(data.get("last_message", "")).lower()
        ):
            print("SUCCESS: Workflow resumed and code executed.")
        else:
            print("Check logs to confirm execution.")

    except Exception as e:
        print(f"Error approving workflow: {e}")


if __name__ == "__main__":
    run_test()
