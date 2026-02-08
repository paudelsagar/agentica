import json
import time

import requests

URL = "http://localhost:8000/run"


def test_memory_persistence():
    # 1. Thread A: Tell the agent a "weird fact"
    thread_a = "memory_test_thread_A"
    fact = "The secret password for the hidden vault is 'Obsidian-77-Gold'."

    print(f"\n--- Thread A: Learning a fact ---")
    payload_a = {
        "thread_id": thread_a,
        "message": f"Please remember this secret for me: {fact}",
    }
    response_a = requests.post(URL, json=payload_a)
    print(f"Agent Response: {response_a.json()['last_message']}")

    # Wait for processing and DB write
    time.sleep(2)

    # 2. Thread B: Ask a DIFFERENT thread/agent about the fact
    thread_b = "memory_test_thread_B"
    print(f"\n--- Thread B: Recalling the fact (New Thread) ---")
    payload_b = {
        "thread_id": thread_b,
        "message": "What was that secret password for the vault I mentioned earlier?",
    }
    response_b = requests.post(URL, json=payload_b)
    last_msg = response_b.json()["last_message"]
    print(f"Agent Response: {last_msg}")

    if "Obsidian-77-Gold" in last_msg:
        print("\nSUCCESS: The agent remembered the fact via Automated RAG!")
    else:
        print(
            "\nFAILURE: The agent did not recall the fact. Check logs for 'proactive_memory_retrieval'."
        )


if __name__ == "__main__":
    test_memory_persistence()
