import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Verify that the root endpoint returns 200 OK and expected API metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ONLINE"
    assert "Yojana Saathi" in data["message"]
    assert data["health_url"] == "/api/v1/health"
    assert data["supported_languages"] == ["en", "hi", "kn", "te"]


def test_health_endpoint():
    """Verify that GET /api/v1/health returns 200 OK and valid health payload."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["HEALTHY", "NEEDS_INITIALIZATION"]
    assert data["version"] == "1.0.0"
    assert "timestamp" in data
    assert data["services"]["backend"] == "READY"
    db_status = data["services"]["database"]
    assert db_status["status"] in ["CONNECTED", "NOT_INITIALIZED"]
    assert "type" in db_status
    assert "schemes_indexed" in db_status
    assert data["supported_languages"] == ["en", "hi", "kn", "te"]

