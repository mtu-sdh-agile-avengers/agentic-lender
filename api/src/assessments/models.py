import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.assessments.enums import AIDecision, AssessmentStatus
from src.utils import _get_utc_now


class VoteModel(BaseModel):
    """How one LLM voted (`assessments.decision.votes`)."""

    provider: str
    decision: AIDecision | None = None  # None if the model did not give a usable answer
    reason: str | None = None


class DecisionModel(BaseModel):
    """Final decision of the AI committee (`assessments.decision`)."""

    decision: AIDecision
    reason: str | None = None
    conditions: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    automatic: bool = False  # declined on a hard limit, no LLM consulted
    votes: list[VoteModel] = Field(default_factory=list)


class AgentStepModel(BaseModel):
    """One step of the committee's reasoning (`assessments/{id}/agent_steps/{id}`)."""

    agent_step_id: str = ""
    step_number: int  # starts from 1
    agent: str  # affordability, valuation, market, strategist, auto_decline, risk
    summary: str


class AssessmentModel(BaseModel):
    """One AI committee run (`loan_applications/{id}/assessments/{id}`)."""

    assessment_id: str
    loan_application_id: str  # parent document; not stored as a field
    requested_by_id: str
    job_id: str | None = None  # None until AL-AI Engine accepted the run
    status: AssessmentStatus = AssessmentStatus.QUEUED
    rate_percent: float

    affordability: dict[str, Any] | None = None
    collateral: dict[str, Any] | None = None
    decision: DecisionModel | None = None
    risk: dict[str, Any] | None = (
        None  # tier, score, approval chance (AL-AI Engine `risk` node)
    )

    error: str | None = None
    created_at: datetime.datetime = Field(default_factory=_get_utc_now)
    finished_at: datetime.datetime | None = None

    @property
    def is_finished(self) -> bool:
        return self.status in (AssessmentStatus.DONE, AssessmentStatus.FAILED)
