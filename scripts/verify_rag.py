import json
import time
import uuid

import requests

BASE_URL = "http://127.0.0.1:8000"


def run_test():
    # 1. Store Memory
    thread_id1 = str(uuid.uuid4())
    print(f"\n--- RAG Test 1: Storing Memory (Thread: {thread_id1}) ---")

    query1 = "My secret project code name is 'Project Omega'. Save this to memory."
    payload1 = {"thread_id": thread_id1, "message": query1}

    try:
        response = requests.post(f"{BASE_URL}/run", json=payload1)
        response.raise_for_status()
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Response: {data.get('last_message')}")

        if (
            "saved" in str(data.get("last_message", "")).lower()
            or "memory" in str(data.get("last_message", "")).lower()
        ):
            print("SUCCESS: Memory storage command processed.")
        else:
            print("WARNING: Did not confirm memory storage explicitly.")
    except Exception as e:
        print(f"Error triggering workflow 1: {e}")
        return

    # 2. Recall Memory (Different Thread)
    thread_id2 = str(uuid.uuid4())
    print(f"\n--- RAG Test 2: Recalling Memory (Thread: {thread_id2}) ---")

    query2 = "What is my secret project code name? Recall it from memory."
    payload2 = {"thread_id": thread_id2, "message": query2}

    try:
        response = requests.post(f"{BASE_URL}/run", json=payload2)
        response.raise_for_status()
        data = response.json()
        print(f"Status: {data.get('status')}")
        print(f"Response: {data.get('last_message')}")

        if "Project Omega" in str(data.get("last_message", "")):
            print("SUCCESS: Memory recalled correctly.")
        else:
            print("FAILURE: Did not recall the correct project name.")

    except Exception as e:
        print(f"Error triggering workflow 2: {e}")


if __name__ == "__main__":
    run_test()
