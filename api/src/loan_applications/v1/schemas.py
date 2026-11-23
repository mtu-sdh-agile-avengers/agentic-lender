import datetime
from typing import Self

from pydantic import Field, model_validator

from src.loan_applications.enums import (
    BerRating,
    County,
    LoanApplicationStatus,
    LtvGroup,
    PropertyType,
    RiskTier,
    UnderwritingOutcome,
)
from src.loan_applications.models import LoanApplicationModel, PropertySpecModel
from src.schemas import BaseSchema, PaginationQuery

# Query + Body Models ---------------------------------------------------------------


class PropertySpecBody(BaseSchema):
    """Part of the body of `POST /api/v1/loan-applications."""

    county: County
    address: str | None = Field(None, max_length=200)
    floor_area_m2: float = Field(ge=20, le=600)
    bedrooms: int = Field(ge=1, le=10)
    bathrooms: int = Field(ge=0, le=10)
    property_type: PropertyType
    ber: BerRating | None = None
    latitude: float | None = Field(None, ge=51.4, le=55.5)
    longitude: float | None = Field(None, ge=-10.6, le=-5.8)
    asking_price: float = Field(gt=0)

    @model_validator(mode="after")
    def _coordinates_come_in_pairs(self) -> Self:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be given together")
        return self

    def to_model(self) -> PropertySpecModel:
        return PropertySpecModel.model_validate(self.model_dump())


class LoanApplicationCreateBody(BaseSchema):
    """Body of `POST /api/v1/loan-applications."""

    broker_id: str | None = Field(None, max_length=128)
    annual_gross_income: float = Field(gt=0)
    annual_debt_repayments: float = Field(ge=0)
    deposit: float = Field(gt=0)
    term_years: int = Field(ge=5, le=40)
    first_time_buyer: bool
    property_spec: PropertySpecBody

    @model_validator(mode="after")
    def _deposit_below_asking_price(self) -> Self:
        if self.deposit >= self.property_spec.asking_price:
            raise ValueError("deposit must be lower than property asking price")
        return self


class LoanApplicationFilterQuery(PaginationQuery):
    """Query parameters of `GET /api/v1/loan-applications` (+ `page`, `pageSize`)."""

    unclaimed_only: bool = False  # i.e., with broker_id == null
    status: LoanApplicationStatus | None = None
    ltv_group: LtvGroup | None = None
    risk_tier: RiskTier | None = None


class BankOfficerAssignBody(BaseSchema):
    """Body of `PUT /api/v1/loan-applications/{id}/bank-officer`"""

    bank_officer_id: str = Field(min_length=1, max_length=128)


class UnderwritingDecisionCreateBody(BaseSchema):
    """Body of `PUT /api/v1/loan-applications/{id}/decision`"""

    outcome: UnderwritingOutcome
    reason: str = Field(min_length=1, max_length=1000)
    conditions: list[str] = Field(default_factory=list, max_length=20)


# Response Models ------------------------------------------------------------


class PropertySpecResponse(BaseSchema):
    county: County
    address: str | None
    floor_area_m2: float
    bedrooms: int
    bathrooms: int
    property_type: PropertyType
    ber: BerRating | None
    latitude: float | None
    longitude: float | None
    asking_price: float


class StatusChangeResponse(BaseSchema):
    status: LoanApplicationStatus
    changed_by_id: str
    changed_at: datetime.datetime


class UnderwritingDecisionResponse(BaseSchema):
    outcome: UnderwritingOutcome
    reason: str
    conditions: list[str]
    decided_by: str
    decided_at: datetime.datetime


class LoanApplicationResponse(BaseSchema):
    loan_application_id: str
    borrower_id: str
    borrower_full_name: str | None
    broker_id: str | None
    bank_officer_id: str | None

    annual_gross_income: float
    annual_debt_repayments: float
    deposit: float
    loan_amount: float
    term_years: int
    first_time_buyer: bool
    ltv: float
    ltv_group: LtvGroup

    property_spec: PropertySpecResponse

    status: LoanApplicationStatus
    status_history: list[StatusChangeResponse]

    assessment_id: str | None
    risk_tier: RiskTier | None

    decision: UnderwritingDecisionResponse | None

    created_at: datetime.datetime
    updated_at: datetime.datetime

    @classmethod
    def from_model(cls, model: LoanApplicationModel) -> Self:
        return cls.model_validate(model.model_dump())
