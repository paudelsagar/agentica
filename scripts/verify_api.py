import json
import uuid

import requests


def main():
    url = "http://localhost:8000/run"
    thread_id = str(uuid.uuid4())
    payload = {
        "thread_id": thread_id,
        "message": "Research 'Agentic AI industry standards' and ask CoderAgent to write a summary file.",
    }

    print(f"Sending request to {url} with thread_id {thread_id}...")
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    main()
