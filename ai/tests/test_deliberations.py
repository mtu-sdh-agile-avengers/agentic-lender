"""Tests for the deliberation endpoints (backlog ALG4-80)."""

import time

import pytest
from fastapi.testclient import TestClient

from app.main import app

APPLICATION = {
    "application_id": "APP-001",
    "income": 85_000, "existing_debt": 4_000, "deposit": 50_000,
    "loan": 300_000, "asking_price": 350_000,
    "rate_percent": 3.9, "term_years": 30,
    "property": {"county": "Cork", "floor_area_m2": 110, "bedrooms": 3,
                 "bathrooms": 2, "property_type": "Semi-D", "ber": "B2"},
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def wait_for(client, job_id: str, timeout: float = 30.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/v1/deliberations/{job_id}").json()
        if body["status"] in ("done", "failed"):
            return body
        time.sleep(0.2)
    pytest.fail(f"job {job_id} did not finish within {timeout}s")


def test_start_returns_202_with_a_job_id(client):
    response = client.post("/v1/deliberations", json=APPLICATION)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert body["poll_url"].endswith(body["job_id"])


def test_run_completes_and_returns_the_full_state(client):
    job_id = client.post("/v1/deliberations", json=APPLICATION).json()["job_id"]
    body = wait_for(client, job_id)

    assert body["status"] == "done"
    result = body["result"]
    assert set(result) >= {"affordability", "valuation", "decision", "trail"}
    assert result["affordability"]["dti_percent"] > 0
    assert len(result["trail"]) >= 2


def test_hopeless_application_is_declined(client):
    hopeless = {**APPLICATION, "application_id": "APP-002",
                "income": 40_000, "loan": 400_000}
    job_id = client.post("/v1/deliberations", json=hopeless).json()["job_id"]
    result = wait_for(client, job_id)["result"]

    assert result["decision"]["decision"] == "Decline"
    assert result["decision"]["automatic"] is True


def test_unknown_job_is_404(client):
    assert client.get("/v1/deliberations/does-not-exist").status_code == 404


def test_invalid_application_is_rejected(client):
    broken = {**APPLICATION, "income": -1}
    assert client.post("/v1/deliberations", json=broken).status_code == 422


def test_property_validation_applies_inside_the_application(client):
    broken = {**APPLICATION,
              "property": {**APPLICATION["property"], "floor_area_m2": 5_000}}
    assert client.post("/v1/deliberations", json=broken).status_code == 422
