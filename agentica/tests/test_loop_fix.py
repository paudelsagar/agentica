import json
import time

import requests


def test_loop_final_validation():
    url = "http://localhost:8000/run"
    payload = {
        "message": "what is the current weather of kathmandu nepal?",
        "thread_id": f"final_loop_test_{int(time.time())}",
    }

    print(f"Testing Query for Loops: {payload['message']}")

    try:
        response = requests.post(url, json=payload, stream=True)
        response.raise_for_status()

        event_count = 0
        agent_sequence = []

        for line in response.iter_lines():
            if line:
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    content = decoded[6:]
                    if content == "[DONE]":
                        break
                    try:
                        data = json.loads(content)
                        if "agent" in data:
                            if (
                                not agent_sequence
                                or agent_sequence[-1] != data["agent"]
                            ):
                                agent_sequence.append(data["agent"])
                                print(f"\n--- {data['agent']} ---")

                        if "content" in data:
                            print(data["content"], end="", flush=True)
                    except:
                        pass

        print(f"\n\nAgent Sequence: {' -> '.join(agent_sequence)}")

        # Validation: Should be Supervisor -> ResearchAgent -> Supervisor -> FINISH
        # Or similar. It should definitely NOT repeat ResearchAgent more than once.
        research_count = agent_sequence.count("ResearchAgent")
        if research_count > 1:
            print(
                f"\nFAIL: Loop detected! ResearchAgent was called {research_count} times."
            )
        else:
            print("\nSUCCESS: No loops detected.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_loop_final_validation()
