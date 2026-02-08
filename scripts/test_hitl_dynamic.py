import json
import time

import requests


def test_hitl_dynamic():
    url = "http://localhost:8000/run"

    print("\n--- Phase 10: Dynamic HITL Test ---")

    # Scenario 1: Autonomous Flow (Research only)
    print("\n1. Testing Autonomous Flow (Research only)...")
    payload_auto = {
        "thread_id": "hitl_auto_test_clean",
        "message": "Research the current population of Mars simulations on Earth.",
    }
    response_auto = requests.post(url, json=payload_auto)
    data_auto = response_auto.json()
    print(f"Status: {data_auto.get('status')}")
    print(f"Last Message: {data_auto.get('last_message')[:200]}...")

    # Scenario 2: HITL Pause (Risky task + Keyword)
    print("\n2. Testing HITL Pause (Risky task + Keyword)...")
    test_thread = f"hitl_danger_test_{int(time.time())}"
    payload_hitl = {
        "thread_id": test_thread,
        "message": "Write a script to simulate a secure system wipe of a temporary directory /tmp/fake_wipe. WAIT FOR MY APPROVAL before you actually execute anything.",
    }
    response_hitl = requests.post(url, json=payload_hitl)
    data_hitl = response_hitl.json()
    print(f"Status: {data_hitl.get('status')}")
    print(f"Last Message: {data_hitl.get('last_message')}")

    if data_hitl.get("status") == "requires_action":
        print(f"\nSUCCESS: Workflow paused correctly for {test_thread}.")

        # Now approve it
        print("\n3. Approving paused task...")
        approve_url = "http://localhost:8000/approve"
        response_approve = requests.post(
            approve_url, json={"thread_id": test_thread, "message": "Approve"}
        )
        data_approve = response_approve.json()
        print(f"Status after approval: {data_approve.get('status')}")
        print(f"Final Message: {data_approve.get('last_message')[:200]}...")
    else:
        print("\nFAILURE: Workflow did not pause for risky task.")


if __name__ == "__main__":
    test_hitl_dynamic()
