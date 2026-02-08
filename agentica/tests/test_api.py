import pytest
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 404  # Assuming no root endpoint defined yet


def test_run_endpoint_basic():
    # Test a simple query
    payload = {"thread_id": "test_thread_123", "message": "Hello, are you there?"}
    response = client.post("/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == "test_thread_123"
    assert data["status"] == "success"
    # assert "last_message" in data # This might vary depending on agent response time or structure
