"""Risk tier and approval chance: agents/risk.py and POST /v1/risk-assessments.

No model file and no network needed: without a model the asking price stands
in for the estimate, exactly like in the committee.
"""

import ast
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.agents.risk import (
    HIGH_FROM,
    MEDIUM_FROM,
    approval_chance,
    assess_risk,
    tier_for,
)
from app.agents.tools import assess_affordability, assess_collateral
from app.main import app

AL_CORE_ENUMS = (
    Path(__file__).resolve().parents[2] / "api/src/loan_applications/enums.py"
)

APPLICATION = {
    "application_id": "APP-RISK",
    "income": 85_000,
    "existing_debt": 4_000,
    "deposit": 50_000,
    "loan": 300_000,
    "asking_price": 350_000,
    "rate_percent": 3.9,
    "term_years": 30,
    "first_time_buyer": True,
    "property": {
        "county": "Cork",
        "floor_area_m2": 110,
        "bedrooms": 3,
        "bathrooms": 2,
        "property_type": "Semi-D",
        "ber": "B2",
    },
}


def risk_of(income, loan, asking_price, estimate=None, existing_debt=0, ftb=True):
    affordability = assess_affordability(
        income, existing_debt, loan, 3.9, 30, first_time_buyer=ftb
    ).as_dict()
    collateral = assess_collateral(loan, asking_price, estimate or asking_price)
    return assess_risk(affordability, collateral)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


# --- scoring ---------------------------------------------------------------
def test_big_deposit_and_high_income_is_low_risk():
    risk = risk_of(income=150_000, loan=200_000, asking_price=400_000)
    assert risk.tier == "Low"
    assert risk.approval_chance_percent >= 90
    assert risk.hard_breaches == []


def test_typical_first_time_buyer_is_medium_risk():
    """85k income, 300k loan on 350k: LTV 86%, LTI 3.5x."""
    risk = risk_of(
        income=85_000, loan=300_000, asking_price=350_000, existing_debt=4_000
    )
    assert risk.tier == "Medium"
    assert 50 <= risk.approval_chance_percent <= 90


def test_breached_limit_is_always_high_with_a_small_chance():
    risk = risk_of(income=40_000, loan=400_000, asking_price=450_000)
    assert risk.tier == "High"
    assert risk.score >= 80
    assert risk.approval_chance_percent <= 5
    assert risk.hard_breaches


def test_second_time_buyer_at_3_8x_income_breaches_but_first_time_does_not():
    first = risk_of(income=80_000, loan=304_000, asking_price=380_000, ftb=True)
    mover = risk_of(income=80_000, loan=304_000, asking_price=380_000, ftb=False)
    assert first.hard_breaches == []
    assert mover.tier == "High"


def test_overpaying_raises_the_risk():
    fair = risk_of(income=90_000, loan=280_000, asking_price=350_000, estimate=350_000)
    over = risk_of(income=90_000, loan=280_000, asking_price=350_000, estimate=300_000)
    assert over.score > fair.score
    assert over.approval_chance_percent < fair.approval_chance_percent


def test_score_is_the_sum_of_the_factors():
    risk = risk_of(
        income=85_000, loan=300_000, asking_price=350_000, existing_debt=4_000
    )
    assert risk.score == round(sum(factor.points for factor in risk.factors))
    assert {factor.factor for factor in risk.factors} == {
        "ltv",
        "lti",
        "dti",
        "overvaluation",
        "income_headroom",
    }
    assert all(0 <= f.points <= f.max_points for f in risk.factors)


def test_tier_boundaries():
    assert tier_for(MEDIUM_FROM - 1) == "Low"
    assert tier_for(MEDIUM_FROM) == "Medium"
    assert tier_for(HIGH_FROM - 1) == "Medium"
    assert tier_for(HIGH_FROM) == "High"


def test_approval_chance_falls_as_risk_rises_and_never_claims_certainty():
    chances = [approval_chance(score) for score in range(0, 101, 5)]
    assert chances == sorted(chances, reverse=True)
    assert 1 <= min(chances) and max(chances) <= 99


def test_tiers_match_al_core_risk_tier():
    """AL-Core stores the tier as its RiskTier enum: the values must match."""
    if not AL_CORE_ENUMS.exists():
        pytest.skip("AL-Core sources not available")
    tree = ast.parse(AL_CORE_ENUMS.read_text(encoding="utf-8"))
    risk_tier = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "RiskTier"
    )
    values = {
        node.value.value
        for node in risk_tier.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
    }
    assert values == {"Low", "Medium", "High"}


# --- POST /v1/risk-assessments --------------------------------------------
def test_endpoint_returns_tier_score_and_chance(client):
    response = client.post("/v1/risk-assessments", json=APPLICATION)
    assert response.status_code == 200
    body = response.json()
    assert body["application_id"] == "APP-RISK"
    assert body["risk"]["tier"] in {"Low", "Medium", "High"}
    assert 0 <= body["risk"]["approval_chance_percent"] <= 100
    assert len(body["risk"]["factors"]) == 5
    assert body["affordability"]["dti_percent"] > 0
    assert body["collateral"]["ltv_percent"] > 0


def test_endpoint_matches_the_committee(client):
    """The instant answer and the committee run agree on the same application."""
    from app.agents.graph import build_committee

    instant = client.post("/v1/risk-assessments", json=APPLICATION).json()["risk"]
    committee = build_committee(model_bundle=None, llm=None).invoke(
        {"application": APPLICATION, "trail": []}
    )
    assert committee["risk"]["tier"] == instant["tier"]
    assert committee["risk"]["score"] == instant["score"]


def test_endpoint_rejects_an_unknown_county(client):
    bad = {**APPLICATION, "property": {**APPLICATION["property"], "county": "Atlantis"}}
    assert client.post("/v1/risk-assessments", json=bad).status_code == 422
