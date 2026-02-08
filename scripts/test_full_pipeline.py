import time
import uuid

import requests


def test_full_pipeline():
    print("Testing Full Multi-Agent Pipeline...")
    thread_id = str(uuid.uuid4())

    # A complex request requiring multiple agents
    message = (
        "Research who the current CEO of Google is. "
        "Then, check if there are any users in our local database with that CEO's name. "
        "Finally, write a python script called 'report.py' that prints the findings."
    )

    payload = {"thread_id": thread_id, "message": message}

    print(f"Sending request: {message[:100]}...")
    response = requests.post("http://localhost:8000/run", json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"Initial Status: {data['status']}")

        # Handle HITL if it pauses for CoderAgent
        if data["status"] == "requires_action":
            print("Approval required for CoderAgent... Sending approval.")
            approve_resp = requests.post(
                "http://localhost:8000/approve",
                json={"thread_id": thread_id, "message": "Proceed"},
            )
            if approve_resp.status_code == 200:
                print("Final Result:")
                print(approve_resp.json()["last_message"])
            else:
                print(f"Approval failed: {approve_resp.text}")
        else:
            print("Final Result:")
            print(data["last_message"])
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    test_full_pipeline()
