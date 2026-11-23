import datetime

from pydantic import BaseModel, Field

from src.loan_applications.enums import LoanApplicationStatus
from src.utils import _get_utc_now


class StressTestResultModel(BaseModel):
    """How one loan application behaves under the scenario (`stress_tests.results`)."""

    loan_application_id: str
    borrower_id: str
    borrower_full_name: str | None = None

    loan_amount: float
    property_value: float  # before the downturn (asking price)

    # interest rate shock
    base_repayment: float  # monthly, at `base_rate_percent`
    stressed_repayment: float  # monthly, at `base_rate_percent` + `rate_shock_bps`
    base_dti_percent: float
    stressed_dti_percent: float
    affordable: bool  # stressed DTI is not above `dti_limit_percent`

    # property market downturn
    base_ltv_percent: float
    stressed_ltv_percent: float
    negative_equity: bool  # loan is larger than the property is now worth


class StressTestModel(BaseModel):
    """One stress test run over a chosen portfolio (`stress_tests/{id}`)."""

    stress_test_id: str
    user_id: str

    statuses: list[
        LoanApplicationStatus
    ]  # portfolio filter; ignored when `loan_application_ids` is given
    loan_application_ids: list[str] | None = None

    rate_shock_bps: int
    price_change_percent: float
    base_rate_percent: float
    dti_limit_percent: float

    results: list[StressTestResultModel]
    created_at: datetime.datetime = Field(default_factory=_get_utc_now)
