"""The shared state that flows through the committee graph (backlog ALG4-80).

This is the single most important structure in the AI Engine. Every node reads
it and writes into it, and whatever it contains at the end is exactly what
AL-Core stores in Firestore and AL-Web renders in the audit console. Changing
it changes the API contract, so change it deliberately.
"""

from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field


def append(existing: list, new: list) -> list:
    """Reducer: nodes add to the trail instead of overwriting it."""
    return (existing or []) + (new or [])


class PropertyInput(BaseModel):
    county: str
    floor_area_m2: float = Field(ge=20, le=600)
    bedrooms: int = Field(ge=1, le=10)
    bathrooms: int = Field(0, ge=0, le=10)
    property_type: str
    ber: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class ApplicationInput(BaseModel):
    """One mortgage application, as AL-Core sends it."""

    application_id: str
    income: float = Field(gt=0, description="Household gross annual income")
    existing_debt: float = Field(0, ge=0, description="Annual debt repayments")
    deposit: float = Field(0, ge=0)
    loan: float = Field(gt=0, description="Requested principal")
    asking_price: float = Field(gt=0)
    rate_percent: float = Field(3.9, gt=0, le=25)
    term_years: int = Field(30, ge=5, le=40)
    first_time_buyer: bool = True
    property: PropertyInput


class AgentStep(BaseModel):
    """One entry in the reasoning trail shown in the audit console."""

    agent: str
    summary: str
    model: str | None = None
    seconds: float | None = None


Decision = Literal["Approve", "Conditionally Approve", "Decline",
                   "Unavailable", "Error"]


class CommitteeState(TypedDict, total=False):
    """Keys are written by nodes; `trail` accumulates rather than overwrites."""

    application: dict[str, Any]
    affordability: dict[str, Any]
    valuation: dict[str, Any]
    market: dict[str, Any]
    decision: dict[str, Any]
    trail: Annotated[list[dict[str, Any]], append]
