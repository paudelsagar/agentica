import json
import time

import requests


def verify_api():
    print("--- Verifying Phase 20: Observability API Extension ---")
    base_url = "http://localhost:8000"

    # 1. Verify /tools
    print("\n[1] Checking /tools...")
    try:
        response = requests.get(f"{base_url}/tools")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            tools = response.json()
            print(f"Total tools found: {len(tools)}")
            if tools:
                print(f"Example tool: {tools[0]['name']} (Owner: {tools[0]['owner']})")
    except Exception as e:
        print(f"Error checking /tools: {e}")

    # 2. Verify /metrics
    print("\n[2] Checking /metrics...")
    try:
        response = requests.get(f"{base_url}/metrics")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            metrics = response.json()
            print("Current Metrics Summary:")
            print(json.dumps(metrics, indent=2))
    except Exception as e:
        print(f"Error checking /metrics: {e}")

    # 3. Verify /state (using a dummy thread_id)
    thread_id = "test_thread_api_verify"
    print(f"\n[3] Checking /state/{thread_id}...")
    try:
        response = requests.get(f"{base_url}/state/{thread_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            state = response.json()
            print("State successfully retrieved.")
    except Exception as e:
        print(f"Error checking /state: {e}")

    # 4. Verify /trajectories
    print(f"\n[4] Checking /trajectories/{thread_id}...")
    try:
        response = requests.get(f"{base_url}/trajectories/{thread_id}")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            trajs = response.json()
            print(f"Trajectories found: {len(trajs)}")
    except Exception as e:
        print(f"Error checking /trajectories: {e}")


if __name__ == "__main__":
    verify_api()
