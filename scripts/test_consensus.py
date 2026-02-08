import asyncio
import json
import time

import requests


def test_consensus():
    print("--- Verifying Phase 17: Multi-Agent Consensus ---")
    url = "http://localhost:8000/run"
    thread_id = f"test_consensus_{int(time.time())}"

    # Task that MUST be flagged as CRITICAL and use multiple agents
    payload = {
        "thread_id": thread_id,
        "message": (
            "URGENT: This is a CRITICAL safety check. We are planning a destructive operation: "
            "permanent deletion of the 'legacy_backup' source code directory. "
            "I require a formal consensus panel consisting of ResearchAgent and CoderAgent. "
            "You MUST output 'CRITICAL' and set 'NEXT AGENT: ResearchAgent, CoderAgent'. "
            "Each agent must then provide a DECISION and REASON."
        ),
    }

    print(f"Sending critical request for thread: {thread_id}...")
    try:
        response = requests.post(url, json=payload, timeout=90)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Final Message Preview: {result['last_message'][:500]}...")

            # Check for Consensus Report in the message
            if "CONSENSUS REPORT" in result[
                "last_message"
            ] or "CONSENSUS REPORT" in str(result):
                print("SUCCESS: Consensus report found in response.")
            else:
                print(
                    "WARNING: Consensus report not explicitly found in last_message. Checking logs might be necessary."
                )
        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    test_consensus()
