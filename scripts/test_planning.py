import json
import time

import requests

SERVER_URL = "http://localhost:8000"
THREAD_ID = "planning_test_1"


def test_planning():
    query = "Research the current price of gold, then find out if we have any 'gold' products in our database tables, and finally suggest which agent should handle a purchase order script."
    print(f"Sending complex query: {query}")

    response = requests.post(
        f"{SERVER_URL}/run", json={"thread_id": THREAD_ID, "message": query}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"Response Status: {data['status']}")
        print(f"Last Message: {data['last_message'][:200]}...")
    else:
        print(f"Error: {response.status_code} - {response.text}")


if __name__ == "__main__":
    test_planning()
