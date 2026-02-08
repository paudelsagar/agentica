import json
import time

import requests


def test_hierarchical_planning():
    print("\n--- Phase 13: Hierarchical Recursive Planning Test ---")

    run_url = "http://localhost:8000/run"
    approve_url = "http://localhost:8000/approve"
    thread_id = f"hierarchy_test_{int(time.time())}"

    # Task that requires DevTeam (Coder + Reviewer)
    payload = {
        "message": "Please implement a robust merge_sort function in Python, write it to a file named 'utils.py', and then have it reviewed for security and performance.",
        "thread_id": thread_id,
    }

    print(f"Request: {payload['message']}")

    try:
        response = requests.post(run_url, json=payload, timeout=120)
        if response.status_code == 200:
            result = response.json()
            print("\n[INITIAL RESPONSE]")
            print(result.get("message", "No message returned."))

            # If the response indicates a pause or is empty (meaning interrupt happened)
            # we send an approval.
            # In our system, interrupt_before=['HITLPause'] means the first call
            # often returns early after the gate node.

            print("\nSending APPROVAL to continue...")
            approval_payload = {"message": "APPROVED", "thread_id": thread_id}
            time.sleep(2)  # Wait for checkpointer to settle

            approve_resp = requests.post(
                approve_url, json=approval_payload, timeout=300
            )
            if approve_resp.status_code == 200:
                final_result = approve_resp.json()
                print("\n[FINAL RESPONSE]")
                print(final_result.get("last_message", "No final message."))

                if "FINAL_RESULT" in str(final_result.get("last_message")):
                    print("\nSUCCESS: Hierarchical delegation (DevTeam) verified.")
                else:
                    print("\nWARNING: Completion marker not found, check server logs.")
            else:
                print(
                    f"Approval failed: {approve_resp.status_code} - {approve_resp.text}"
                )
        else:
            print(f"Run failed: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Connection failed: {e}. Is the server running?")


if __name__ == "__main__":
    test_hierarchical_planning()
