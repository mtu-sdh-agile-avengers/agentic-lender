"""County names: one spelling everywhere (AI engine, training data, AL-Core)."""

import ast
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.counties import COUNTIES, normalize_county
from app.main import app

AI_ROOT = Path(__file__).resolve().parents[1]
AL_CORE_ENUMS = AI_ROOT.parent / "api/src/loan_applications/enums.py"


def test_there_are_26_counties():
    assert len(COUNTIES) == len(set(COUNTIES)) == 26


def test_matches_the_training_data_centroids():
    centroids = json.loads(
        (AI_ROOT / "app/data/county_centroids.json").read_text(encoding="utf-8")
    )
    assert set(centroids) == set(COUNTIES)


def test_matches_al_core_county_enum():
    """AL-Core sends these values; a typo there means a 422 here."""
    if not AL_CORE_ENUMS.exists():
        pytest.skip("AL-Core sources not available")
    tree = ast.parse(AL_CORE_ENUMS.read_text(encoding="utf-8"))
    county = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "County"
    )
    values = {
        node.value.value
        for node in county.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
    }
    assert values == set(COUNTIES)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Cork", "Cork"),
        (" limerick ", "Limerick"),
        ("LEITRIM", "Leitrim"),
        ("Co. Cork", "Cork"),
        ("co cork", "Cork"),
        ("County  Dublin", "Dublin"),
    ],
)
def test_normalises_case_spaces_and_prefix(raw, expected):
    assert normalize_county(raw) == expected


@pytest.mark.parametrize("raw", ["Letrim", "Atlantis", "", "Belfast"])
def test_rejects_unknown_counties(raw):
    with pytest.raises(ValueError):
        normalize_county(raw)


def test_deliberation_rejects_unknown_county_up_front():
    """Before this, a bad county only failed inside the committee run."""
    application = {
        "application_id": "APP-COUNTY",
        "income": 85_000,
        "loan": 300_000,
        "asking_price": 350_000,
        "property": {
            "county": "Letrim",
            "floor_area_m2": 110,
            "bedrooms": 3,
            "property_type": "Semi-D",
        },
    }
    with TestClient(app) as client:
        assert client.post("/v1/deliberations", json=application).status_code == 422
        application["property"]["county"] = " leitrim"
        assert client.post("/v1/deliberations", json=application).status_code == 202
