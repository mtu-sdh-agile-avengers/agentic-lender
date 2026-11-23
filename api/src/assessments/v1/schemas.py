import datetime
from typing import Any, Self

from src.assessments.enums import AIDecision, AssessmentStatus
from src.assessments.service import AssessmentView
from src.schemas import BaseSchema


class VoteResponse(BaseSchema):
    provider: str
    decision: AIDecision | None
    reason: str | None


class DecisionResponse(BaseSchema):
    decision: AIDecision
    reason: str | None
    conditions: list[str]
    key_risks: list[str]
    automatic: bool
    votes: list[VoteResponse]


class AgentStepResponse(BaseSchema):
    step_number: int
    agent: str
    summary: str


class AssessmentResponse(BaseSchema):
    """Response of `POST .../assessments` and `GET .../assessments/latest`: the verdict and how it was reached."""

    assessment_id: str
    loan_application_id: str
    status: AssessmentStatus
    rate_percent: float

    decision: DecisionResponse | None
    affordability: dict[str, Any] | None
    collateral: dict[str, Any] | None
    risk: dict[str, Any] | None
    steps: list[AgentStepResponse]

    error: str | None
    created_at: datetime.datetime
    finished_at: datetime.datetime | None

    @classmethod
    def from_view(cls, view: AssessmentView) -> Self:
        return cls.model_validate(
            {
                **view.assessment.model_dump(),
                "steps": [
                    step.model_dump()
                    for step in sorted(view.steps, key=lambda s: s.step_number)
                ],
            }
        )
