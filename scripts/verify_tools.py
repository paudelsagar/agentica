import json
import time
import uuid

import requests


def main():
    url = "http://localhost:8000/run"
    thread_id = str(uuid.uuid4())

    # Test 1: Research (Real Web Search)
    print("Test 1: Testing ResearchAgent with DuckDuckGo...")
    payload = {
        "thread_id": thread_id,
        "message": "What is the current price of Bitcoin in USD? Search for it.",
    }

    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json().get('last_message')}")
    except Exception as e:
        print(f"Request failed: {e}")

    # Test 2: Coding (Write and Execute)
    print("\nTest 2: Testing CoderAgent with Code Execution...")
    thread_id_2 = str(uuid.uuid4())
    payload = {
        "thread_id": thread_id_2,
        "message": "Create a file named 'timestamp.txt' containing the current timestamp. Then read the file to verify it.",
    }
    try:
        response = requests.post(url, json=payload)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json().get('last_message')}")
    except Exception as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    main()
