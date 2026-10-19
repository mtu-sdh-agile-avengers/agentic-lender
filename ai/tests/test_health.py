"""Tests for the service skeleton (ALG4-79)."""

from fastapi.testclient import TestClient

from app.main import app


def test_health_is_ok():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "al-ai-engine"


def test_ready_reports_model_state():
    """/ready answers 200 when the model is loaded, 503 when it is not."""
    with TestClient(app) as client:
        response = client.get("/ready")
    body = response.json()
    assert response.status_code == (200 if body["model_loaded"] else 503)
    assert set(body["providers"]) == {"groq", "gemini", "ollama"}


def test_openapi_is_generated():
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
    assert "/health" in schema["paths"]
    assert schema["info"]["title"] == "AL-AI Engine"
