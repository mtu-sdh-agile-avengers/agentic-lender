"""Tests for POST /v1/valuations (backlog ALG4-77).

The trained model is not in Git (it is ~95 MB), so tests that need a real
prediction skip themselves when it is missing. Validation tests always run,
including in CI.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

VALID = {
    "county": "Cork",
    "floor_area_m2": 110,
    "bedrooms": 3,
    "bathrooms": 2,
    "property_type": "Semi-D",
    "ber": "B2",
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def model_client(client):
    if getattr(client.app.state, "model_bundle", None) is None:
        pytest.skip("no trained model available; run ml/train_avm.py")
    return client


# --- validation: runs everywhere ------------------------------------------
def test_unknown_county_is_rejected(client):
    response = client.post("/v1/valuations", json={**VALID, "county": "Atlantis"})
    assert response.status_code == 422


def test_floor_area_out_of_range_is_rejected(client):
    response = client.post("/v1/valuations", json={**VALID, "floor_area_m2": 5000})
    assert response.status_code == 422


def test_invalid_ber_is_rejected(client):
    """SI_666 is an exemption code, not a rating."""
    response = client.post("/v1/valuations", json={**VALID, "ber": "SI_666"})
    assert response.status_code == 422


def test_latitude_without_longitude_is_rejected(client):
    response = client.post("/v1/valuations", json={**VALID, "latitude": 51.9})
    assert response.status_code == 422


def test_counties_endpoint_lists_26_counties(client):
    counties = client.get("/v1/valuations/counties").json()
    assert len(counties) == 26
    assert "Cork" in counties
    assert "Antrim" not in counties  # Northern Ireland was excluded


# --- prediction: needs the trained model ----------------------------------
def test_valuation_returns_estimate_and_range(model_client):
    body = model_client.post("/v1/valuations", json=VALID).json()
    assert body["estimate"] > 0
    assert body["range"]["low"] < body["estimate"] < body["range"]["high"]
    assert body["coordinates_source"] == "county_centroid"
    assert body["ber_known"] is True


def test_asking_price_comparison(model_client):
    body = model_client.post(
        "/v1/valuations", json={**VALID, "asking_price": 2_000_000}).json()
    assert body["comparison"]["overvalued"] is True
    assert body["comparison"]["gap_percent"] > 10


def test_supplied_coordinates_are_used(model_client):
    body = model_client.post(
        "/v1/valuations",
        json={**VALID, "latitude": 51.90, "longitude": -8.47}).json()
    assert body["coordinates_source"] == "request"


def test_dublin_costs_more_than_leitrim(model_client):
    """Sanity check: the model should still understand Irish geography."""
    dublin = model_client.post(
        "/v1/valuations", json={**VALID, "county": "Dublin"}).json()
    leitrim = model_client.post(
        "/v1/valuations", json={**VALID, "county": "Leitrim"}).json()
    assert dublin["estimate"] > leitrim["estimate"]


def test_missing_ber_is_allowed(model_client):
    body = model_client.post(
        "/v1/valuations", json={**VALID, "ber": None}).json()
    assert body["ber_known"] is False
    assert body["estimate"] > 0
