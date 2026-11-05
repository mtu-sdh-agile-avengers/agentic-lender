"""Tests for the credit committee (backlog ALG4-80).

No network and no model file needed: the language model is a fake function and
the valuation falls back to the asking price when no bundle is injected.
"""

import json

import pytest

from app.agents.graph import build_committee
from app.agents.tools import (
    DTI_LIMIT_PCT,
    LTI_LIMIT,
    assess_affordability,
    assess_collateral,
    monthly_repayment,
)

HEALTHY = {
    "application_id": "APP-TEST",
    "income": 85_000, "existing_debt": 4_000, "deposit": 50_000,
    "loan": 300_000, "asking_price": 350_000,
    "rate_percent": 3.9, "term_years": 30,
    "property": {"county": "Cork", "floor_area_m2": 110, "bedrooms": 3,
                 "bathrooms": 2, "property_type": "Semi-D", "ber": "B2"},
}
HOPELESS = {**HEALTHY, "income": 40_000, "loan": 400_000}


# --- deterministic tools --------------------------------------------------
def test_monthly_repayment_matches_annuity_formula():
    # 300,000 over 30 years at 3.9% is about 1,415 per month
    assert round(monthly_repayment(300_000, 0.039, 30)) == 1415


def test_zero_rate_is_simple_division():
    assert monthly_repayment(360_000, 0, 30) == 1000


def test_stressed_repayment_is_higher_than_the_offered_rate():
    result = assess_affordability(85_000, 4_000, 300_000, 3.9, 30)
    assert result.stressed_repayment > result.monthly_repayment


def test_healthy_application_has_no_breaches():
    result = assess_affordability(85_000, 4_000, 300_000, 3.9, 30)
    assert result.breaches == []
    assert result.lti_multiple < LTI_LIMIT
    assert result.dti_percent < DTI_LIMIT_PCT


def test_hopeless_application_breaches_both_limits():
    result = assess_affordability(40_000, 4_000, 400_000, 3.9, 30)
    assert len(result.breaches) == 2


def test_ltv_uses_the_lower_of_asking_price_and_estimate():
    """Lending against the higher figure would understate the risk."""
    cheap_estimate = assess_collateral(300_000, 350_000, 300_000)
    assert cheap_estimate["ltv_basis"] == "model estimate"
    assert cheap_estimate["ltv_percent"] == 100.0
    assert cheap_estimate["breaches"]           # above the 90% limit

    high_estimate = assess_collateral(300_000, 350_000, 400_000)
    assert high_estimate["ltv_basis"] == "asking price"
    assert high_estimate["ltv_percent"] == pytest.approx(85.7, abs=0.1)


def test_overvalued_flag_triggers_above_ten_percent():
    assert assess_collateral(300_000, 450_000, 400_000)["overvalued"] is True
    assert assess_collateral(300_000, 405_000, 400_000)["overvalued"] is False


# --- the graph ------------------------------------------------------------
def fake_llm(_prompt: str) -> str:
    return json.dumps({"decision": "Approve", "conditions": [],
                       "key_risks": [], "reason": "fake model"})


def run(application: dict, llm=fake_llm):
    committee = build_committee(model_bundle=None, llm=llm)
    return committee.invoke({"application": application, "trail": []})


def test_healthy_application_reaches_the_strategist():
    final = run(HEALTHY)
    assert final["decision"]["decision"] == "Approve"
    assert [step["agent"] for step in final["trail"]] == [
        "affordability", "valuation", "market", "strategist"]


def test_hopeless_application_is_declined_without_an_llm_call():
    calls = []

    def spy(prompt):
        calls.append(prompt)
        return fake_llm(prompt)

    final = run(HOPELESS, llm=spy)
    assert final["decision"]["decision"] == "Decline"
    assert final["decision"]["automatic"] is True
    assert calls == []          # the whole point of the conditional edge
    assert [step["agent"] for step in final["trail"]] == [
        "affordability", "auto_decline"]


def test_unparseable_model_output_is_reported_not_raised():
    final = run(HEALTHY, llm=lambda _: "Sure! Here is my answer: approve.")
    assert final["decision"]["decision"] == "Error"


def test_markdown_fenced_json_is_accepted():
    """Models often wrap JSON in code fences."""
    fenced = '```json\n{"decision": "Decline", "reason": "test"}\n```'
    assert run(HEALTHY, llm=lambda _: fenced)["decision"]["decision"] == "Decline"


def test_provider_outage_does_not_crash_the_run():
    def broken(_prompt):
        raise ConnectionError("provider down")

    final = run(HEALTHY, llm=broken)
    assert final["decision"]["decision"] == "Unavailable"
    assert final["valuation"]["ltv_percent"] > 0     # earlier work is preserved


def test_missing_provider_still_produces_a_full_trail():
    final = run(HEALTHY, llm=None)
    assert final["decision"]["decision"] == "Unavailable"
    assert len(final["trail"]) == 4


# --- voting path (ALG4-85) -------------------------------------------------
def test_committee_can_decide_by_vote():
    """The strategist can run across several providers instead of one."""
    from app.llm.providers import Provider

    def provider(name, decision):
        payload = json.dumps({"decision": decision, "conditions": [],
                              "key_risks": [], "reason": f"{name}"})
        return Provider(name=name, model=f"{name}-x", call=lambda _p: payload)

    committee = build_committee(
        model_bundle=None,
        providers=[provider("groq", "Approve"), provider("gemini", "Approve"),
                   provider("ollama", "Decline")])
    final = committee.invoke({"application": HEALTHY, "trail": []})

    decision = final["decision"]
    assert decision["decision"] == "Approve"       # 2 of 3
    assert decision["agreement"] == pytest.approx(0.67, abs=0.01)
    assert len(decision["votes"]) == 3             # all three kept for the audit
