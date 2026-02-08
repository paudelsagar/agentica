import time
import uuid

import requests


def test_data_agent():
    print("Testing DataAgent via API...")
    thread_id = str(uuid.uuid4())

    # Question that should trigger DataAgent
    payload = {
        "thread_id": thread_id,
        "message": "List all the tables in the database and tell me how many users are in the 'users' table.",
    }

    response = requests.post("http://localhost:8000/run", json=payload)
    if response.status_code == 200:
        data = response.json()
        print(f"Status: {data['status']}")
        print(f"Response: {data['last_message']}")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    test_data_agent()
