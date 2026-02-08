import json
import sys
import time
import uuid

import requests

BASE_URL = "http://localhost:8000"


def run_test():
    thread_id = str(uuid.uuid4())
    print(f"Starting Dynamic Tool Verification Test (Thread ID: {thread_id})")

    # Step 1: Create a new tool
    # We ask the agent to create a tool.
    payload = {
        "thread_id": thread_id,
        "message": "Create a new tool called 'get_server_time' in a file 'server_time_tool.py'. The tool should return the current time as a string. Use the @tool decorator from langchain_core.tools.",
    }

    try:
        print(f"Sending request 1 (Create Tool): {payload['message']}")
        response = requests.post(f"{BASE_URL}/run", json=payload)
        response.raise_for_status()
        data = response.json()
        print("\n--- Response 1 ---")
        print(json.dumps(data, indent=2))

        # Handle Approval if needed
        if data.get("status") == "requires_action":
            print(f"\nWorklow paused. Sending approval for thread {thread_id}...")
            # We need to send approval to resume
            # The /approve endpoint expects RunRequest (thread_id, message)
            # Message can be empty or "proceed"
            approve_payload = {"thread_id": thread_id, "message": "proceed"}
            response = requests.post(f"{BASE_URL}/approve", json=approve_payload)
            response.raise_for_status()
            data = response.json()
            print("\n--- Response 1 (After Approval) ---")
            print(json.dumps(data, indent=2))

        # Step 2: Use the new tool
        # We ask the agent to use the tool we just created.
        # Use a new thread to verify the tool is globally available and avoid Supervisor confusion.
        thread_id_2 = str(uuid.uuid4())
        payload2 = {
            "thread_id": thread_id_2,
            "message": "Write a python script to use the 'get_server_time' tool regarding the current time and print the result.",
        }

        print(f"\nSending request 2 (Use Tool): {payload2['message']}")
        response = requests.post(f"{BASE_URL}/run", json=payload2)
        response.raise_for_status()
        data = response.json()
        print("\n--- Response 2 ---")
        print(json.dumps(data, indent=2))

        # Handle Approval for step 2 if needed
        if data.get("status") == "requires_action":
            print(f"\nWorklow paused. Sending approval for thread {thread_id_2}...")
            approve_payload = {"thread_id": thread_id_2, "message": "proceed"}
            response = requests.post(f"{BASE_URL}/approve", json=approve_payload)
            response.raise_for_status()
            data = response.json()
            print("\n--- Response 2 (After Approval) ---")
            print(json.dumps(data, indent=2))

        # Check if the tool was actually called
        # We can look at the logs or check the response content for time.
        # Ideally, we'd see "executing_tool" with "get_server_time" in the logs.

        print("\nTest Completed. Check server logs for 'get_server_time' execution.")

    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_test()
