import datetime
from typing import Self

from pydantic import Field, model_validator

from src.loan_applications.enums import LoanApplicationStatus
from src.schemas import BaseSchema
from src.stress_tests.models import StressTestModel


class StressTestCreateBody(BaseSchema):
    """Body of `POST /api/v1/stress-tests`."""

    # central bank rate shock; 0 (no shock) or +100..+300 bps
    rate_shock_bps: int = Field(0, ge=0, le=300, examples=[200])

    # property market downturn; 0 (no change) or a fall down to -60%
    price_change_percent: float = Field(0, ge=-60, le=0, examples=[-15])

    statuses: list[LoanApplicationStatus] | None = Field(
        None, description="Portfolio filter; every status except `Closed` by default"
    )
    loan_application_ids: list[str] | None = Field(
        None,
        min_length=1,
        max_length=300,
        description="Concrete applications; `statuses` is ignored then",
    )

    @model_validator(mode="after")
    def _valid_scenario(self) -> Self:
        if 0 < self.rate_shock_bps < 100:
            raise ValueError("rate_shock_bps must be 0 or between 100 and 300")
        if self.rate_shock_bps == 0 and self.price_change_percent == 0:
            raise ValueError("set rate_shock_bps and/or price_change_percent")
        return self


class StressTestResultResponse(BaseSchema):
    loan_application_id: str
    borrower_id: str
    borrower_full_name: str | None
    loan_amount: float
    property_value: float
    base_repayment: float
    stressed_repayment: float
    base_dti_percent: float
    stressed_dti_percent: float
    affordable: bool
    base_ltv_percent: float
    stressed_ltv_percent: float
    negative_equity: bool


class StressTestSummaryResponse(BaseSchema):
    """Totals computed from `results` (not stored)."""

    applications_tested: int
    not_affordable_count: int
    negative_equity_count: int
    exposure_at_risk: (
        float  # loan amount of borrowers who are not affordable or in negative equity
    )

    @classmethod
    def from_model(cls, model: StressTestModel) -> Self:
        at_risk = [r for r in model.results if not r.affordable or r.negative_equity]
        return cls(
            applications_tested=len(model.results),
            not_affordable_count=sum(not r.affordable for r in model.results),
            negative_equity_count=sum(r.negative_equity for r in model.results),
            exposure_at_risk=round(sum(r.loan_amount for r in at_risk), 2),
        )


class StressTestListItemResponse(BaseSchema):
    stress_test_id: str
    rate_shock_bps: int
    price_change_percent: float
    summary: StressTestSummaryResponse
    created_at: datetime.datetime

    @classmethod
    def from_model(cls, model: StressTestModel) -> Self:
        return cls(
            stress_test_id=model.stress_test_id,
            rate_shock_bps=model.rate_shock_bps,
            price_change_percent=model.price_change_percent,
            summary=StressTestSummaryResponse.from_model(model),
            created_at=model.created_at,
        )


class StressTestResponse(BaseSchema):
    stress_test_id: str
    statuses: list[LoanApplicationStatus]
    loan_application_ids: list[str] | None
    rate_shock_bps: int
    price_change_percent: float
    base_rate_percent: float
    dti_limit_percent: float
    summary: StressTestSummaryResponse
    results: list[StressTestResultResponse]
    created_at: datetime.datetime

    @classmethod
    def from_model(cls, model: StressTestModel) -> Self:
        return cls.model_validate(
            {
                **model.model_dump(),
                "summary": StressTestSummaryResponse.from_model(model),
            }
        )
