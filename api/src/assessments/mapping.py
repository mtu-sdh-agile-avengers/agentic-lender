"""Translation between AL-Core models and the AL-AI Engine contract (pure functions, no I/O)."""

from dataclasses import dataclass, field
from typing import Any

from src.assessments.enums import AIDecision, AssessmentStatus
from src.assessments.models import AgentStepModel, DecisionModel, VoteModel
from src.loan_applications.enums import RiskTier
from src.loan_applications.models import LoanApplicationModel
from src.utils import _get_utc_now

# `PropertyInput` fields of AL-AI Engine; `address` and `asking_price` are not sent
_PROPERTY_FIELDS = {
    "county",
    "floor_area_m2",
    "bedrooms",
    "bathrooms",
    "property_type",
    "ber",
    "latitude",
    "longitude",
}


def to_engine_input(
    application: LoanApplicationModel, rate_percent: float
) -> dict[str, Any]:
    """Builds `ApplicationInput` of AL-AI Engine. No names, emails or addresses leave AL-Core.

    Args:
        application: loan application to assess.
        rate_percent: interest rate the committee calculates repayments with.

    Returns:
        dict[str, Any]: JSON body of `POST /v1/deliberations`.
    """
    return {
        "application_id": application.loan_application_id,
        "income": application.annual_gross_income,
        "existing_debt": application.annual_debt_repayments,
        "deposit": application.deposit,
        "loan": application.loan_amount,
        "asking_price": application.property_spec.asking_price,
        "rate_percent": rate_percent,
        "term_years": application.term_years,
        "first_time_buyer": application.first_time_buyer,
        "property": application.property_spec.model_dump(
            mode="json", include=_PROPERTY_FIELDS
        ),
    }


@dataclass(frozen=True)
class EngineResult:
    fields: dict[str, Any]  # assessment fields to save
    steps: list[AgentStepModel] = field(default_factory=list)
    risk_tier: RiskTier | None = None  # copied to `loan_applications.risk_tier`


def from_engine_result(result: dict[str, Any]) -> EngineResult:
    """Converts the final committee state returned by AL-AI Engine into what AL-Core stores.

    Args:
        result: `result` of a finished `GET /v1/deliberations/{job_id}`.

    Returns:
        EngineResult: assessment fields, ordered reasoning steps and the risk tier.
    """
    raw_decision: dict[str, Any] = result.get("decision") or {}

    decision = DecisionModel(
        decision=AIDecision(raw_decision.get("decision", AIDecision.ERROR)),
        reason=raw_decision.get("reason"),
        conditions=list(raw_decision.get("conditions") or []),
        key_risks=list(raw_decision.get("key_risks") or []),
        automatic=bool(raw_decision.get("automatic", False)),
        votes=[
            VoteModel(
                provider=vote["provider"],
                decision=vote.get("decision"),
                reason=vote.get("reason"),
            )
            for vote in raw_decision.get("votes") or []
        ],
    )

    steps = [
        AgentStepModel(
            step_number=number,
            agent=str(step.get("agent", "unknown")),
            summary=str(step.get("summary", "")),
        )
        for number, step in enumerate(result.get("trail") or [], start=1)
    ]

    risk: dict[str, Any] | None = result.get("risk")
    risk_tier = (
        RiskTier(risk["tier"]) if risk and risk.get("tier") in RiskTier else None
    )

    fields = {
        "status": AssessmentStatus.DONE,
        "affordability": result.get("affordability"),
        "collateral": result.get("valuation"),
        "decision": decision.model_dump(),
        "risk": risk,
        "finished_at": _get_utc_now(),
    }
    return EngineResult(fields=fields, steps=steps, risk_tier=risk_tier)
