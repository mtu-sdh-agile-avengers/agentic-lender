"""POST /v1/risk-assessments - instant risk tier and approval chance.

AL-Core calls it when an application is submitted and stores `risk.tier` in
`loan_applications.risk_tier`, so brokers and officers can filter by risk
before any committee run. No language model is involved, so the answer comes
back immediately. It uses the same calculators as the committee, whose result
carries the same block under `result.risk`.
"""

import logging

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.agents.graph import affordability_node, valuation_node
from app.agents.risk import RiskAssessment, assess_risk
from app.agents.state import ApplicationInput
from app.deps import InternalAuth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["risk"], dependencies=[InternalAuth])


class RiskAssessmentResponse(BaseModel):
    application_id: str
    risk: RiskAssessment
    affordability: dict = Field(description="Same block as in a committee result")
    collateral: dict = Field(
        description="Same block as `valuation` in a committee result; the "
        "asking price stands in for the estimate when the model is not loaded"
    )


@router.post(
    "/risk-assessments",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
)
async def create_risk_assessment(
    application: ApplicationInput, http_request: Request
) -> RiskAssessmentResponse:
    """Risk tier (Low / Medium / High), risk score and approval chance."""
    state = {"application": application.model_dump()}
    affordability = affordability_node(state)["affordability"]
    model_bundle = getattr(http_request.app.state, "model_bundle", None)
    collateral = valuation_node(state, model_bundle=model_bundle)["valuation"]

    risk = assess_risk(affordability, collateral)
    logger.info(
        "risk %s: %s, score %s, approval chance %s%%",
        application.application_id,
        risk.tier,
        risk.score,
        risk.approval_chance_percent,
    )
    return RiskAssessmentResponse(
        application_id=application.application_id,
        risk=risk,
        affordability=affordability,
        collateral=collateral,
    )
