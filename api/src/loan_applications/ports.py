from typing import Protocol, Callable

from pydantic import BaseModel

from src.loan_applications.enums import LoanApplicationStatus, LtvGroup, RiskTier
from src.loan_applications.models import LoanApplicationModel, UserInfoModel
from src.schemas import PaginatedResponse


class LoanApplicationQuery(BaseModel, frozen=True):
    borrower_id: str | None = None
    broker_id: str | None = None
    bank_officer_id: str | None = None

    unclaimed_only: bool = False  # i.e., with broker_id == null
    status: LoanApplicationStatus | None = None
    ltv_group: LtvGroup | None = None
    risk_tier: RiskTier | None = None

    page: int = 1
    page_size: int = 15


class LoanApplicationRepositoryPort(Protocol):
    def next_id(self) -> str: ...

    async def add_loan_application(self, application: LoanApplicationModel) -> None: ...
    async def get_loan_application(
        self, application_id: str
    ) -> LoanApplicationModel | None: ...

    async def get_loan_applications(
        self, query: LoanApplicationQuery
    ) -> PaginatedResponse[LoanApplicationModel]: ...
    async def update_loan_application(
        self, application_id: str, mutator: Callable[[LoanApplicationModel], None]
    ) -> LoanApplicationModel: ...


# required, so loan application service would not be able to add account or get excessive data
class UserInfoSearchGatewayPort(Protocol):
    async def find_user(self, uid: str) -> UserInfoModel: ...
