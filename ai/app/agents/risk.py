"""Risk tier and approval chance of a mortgage application.

Deterministic, like the other calculators: the same application always gets
the same tier, whether it comes from POST /v1/risk-assessments (instant, used
by AL-Core to fill `loan_applications.risk_tier` on submission) or from the
committee run (`result.risk`).

How it works. Five factors add up to a risk score from 0 (safest) to 100:

    factor                          0 points at        full points at   max
    loan-to-value                   60%                90%              25
    loan-to-income                  2.5x               the CBI limit    25
    stressed debt-to-income         25%                40%              25
    asking price above estimate     0%                 20%              15
    income left after repayments    EUR 2,500/month    EUR 1,000/month  10

Tier: Low below 35, Medium from 35, High from 65. A breached hard limit
(LTV, LTI or stressed DTI) always means High.

The approval chance turns the score into "how likely is this application to be
approved under our lending criteria" with a logistic curve: about 92% at the
Low/Medium boundary, 50% at a score of 55 and about 22% at the Medium/High
boundary. A breached hard limit caps it at 5%, because such an application is
declined automatically. It is an estimate from the criteria, not a probability
learned from past loans: we have no repayment history to learn one from.
"""

import math
from typing import Literal

from pydantic import BaseModel, Field

from app.agents.tools import LTV_LIMIT_PCT

RISK_VERSION = "risk-rules-v1"

# Same values as AL-Core's RiskTier (api/src/loan_applications/enums.py)
RiskTier = Literal["Low", "Medium", "High"]

MEDIUM_FROM = 35  # risk score at which the tier becomes Medium
HIGH_FROM = 65  # ... and High
BREACH_MIN_SCORE = 80  # a breached hard limit puts the score at least here
BREACH_MAX_CHANCE = 5  # ... and the approval chance at most here

# Logistic curve from risk score to approval chance
_CHANCE_MIDPOINT = 55  # score with a 50% approval chance
_CHANCE_SPREAD = 8  # smaller = steeper


class RiskFactor(BaseModel):
    factor: Literal["ltv", "lti", "dti", "overvaluation", "income_headroom"]
    label: str
    value: float
    unit: str
    points: float = Field(description="Contribution to the risk score")
    max_points: float


class RiskAssessment(BaseModel):
    tier: RiskTier = Field(description="Same values as AL-Core RiskTier")
    score: int = Field(ge=0, le=100, description="0 = safest, 100 = riskiest")
    approval_chance_percent: int = Field(
        ge=0, le=100, description="Estimated chance of approval under our criteria"
    )
    factors: list[RiskFactor]
    hard_breaches: list[str] = Field(
        description="Breached regulatory or policy limits; any breach means High"
    )
    ltv_basis: Literal["asking price", "model estimate"]
    thresholds: dict[str, int] = {
        "medium_from": MEDIUM_FROM,
        "high_from": HIGH_FROM,
    }
    version: str = RISK_VERSION
    note: str = (
        "Estimated from lending criteria (LTV, LTI, stressed DTI, asking price "
        "against the model estimate, income left after repayments). Not a "
        "probability learned from repayment history."
    )


def _scale(value: float, start: float, end: float, max_points: float) -> float:
    """0 points at `start`, `max_points` at `end`, linear in between.

    Works in both directions: `start` may be larger than `end` (for factors
    where less is riskier, like income left over).
    """
    if start == end:
        return max_points if value >= end else 0.0
    share = (value - start) / (end - start)
    return max(0.0, min(1.0, share)) * max_points


def tier_for(score: float) -> RiskTier:
    if score >= HIGH_FROM:
        return "High"
    if score >= MEDIUM_FROM:
        return "Medium"
    return "Low"


def approval_chance(score: float) -> int:
    """Logistic curve, clamped to 1..99: certainty is never claimed."""
    chance = 100 / (1 + math.exp((score - _CHANCE_MIDPOINT) / _CHANCE_SPREAD))
    return int(min(99, max(1, round(chance))))


def assess_risk(affordability: dict, collateral: dict) -> RiskAssessment:
    """Score an application from the affordability and collateral calculators.

    Args:
        affordability: `Affordability.as_dict()` (tools.assess_affordability).
        collateral: `tools.assess_collateral(...)`; when no valuation was run,
            pass it with the asking price as the estimate (gap 0%).
    """
    ltv = collateral["ltv_percent"]
    lti = affordability["lti_multiple"]
    lti_limit = affordability["limits"]["lti"]
    dti = affordability["dti_percent"]
    dti_limit = affordability["limits"]["dti_percent"]
    gap = collateral["gap_percent"]
    disposable_monthly = affordability["disposable_annual"] / 12

    factors = [
        RiskFactor(
            factor="ltv",
            label="Loan-to-value",
            value=ltv,
            unit="%",
            points=_scale(ltv, 60, 80, 10) + _scale(ltv, 80, LTV_LIMIT_PCT, 15),
            max_points=25,
        ),
        RiskFactor(
            factor="lti",
            label="Loan-to-income",
            value=lti,
            unit="x",
            points=_scale(lti, 2.5, lti_limit, 25),
            max_points=25,
        ),
        RiskFactor(
            factor="dti",
            label="Stressed debt-to-income",
            value=dti,
            unit="%",
            points=_scale(dti, 25, dti_limit, 25),
            max_points=25,
        ),
        RiskFactor(
            factor="overvaluation",
            label="Asking price above estimate",
            value=gap,
            unit="%",
            points=_scale(gap, 0, 10, 10) + _scale(gap, 10, 20, 5),
            max_points=15,
        ),
        RiskFactor(
            factor="income_headroom",
            label="Income left after repayments",
            value=round(disposable_monthly),
            unit="EUR/month",
            points=_scale(disposable_monthly, 2_500, 1_000, 10),
            max_points=10,
        ),
    ]
    for factor in factors:
        factor.points = round(factor.points, 1)

    breaches = list(affordability["breaches"]) + list(collateral["breaches"])
    score = int(round(min(100.0, sum(factor.points for factor in factors))))
    chance = approval_chance(score)
    if breaches:
        score = max(score, BREACH_MIN_SCORE)
        chance = min(chance, BREACH_MAX_CHANCE)

    return RiskAssessment(
        tier="High" if breaches else tier_for(score),
        score=score,
        approval_chance_percent=chance,
        factors=factors,
        hard_breaches=breaches,
        ltv_basis=collateral["ltv_basis"],
    )
