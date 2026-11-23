from collections.abc import Callable

from src.auth.enums import UserRole
from src.auth.models import CurrentUserModel
from src.loan_applications.access import (
    has_modify_access,
    has_view_access,
    ASSIGNEE_FIELD,
)
from src.loan_applications.enums import (
    LoanApplicationStatus,
    LtvGroup,
    RiskTier,
    UnderwritingOutcome,
)
from src.loan_applications.exceptions import (
    LoanApplicationAccessError,
    LoanApplicationInvalidAssigneeError,
    LoanApplicationNotFoundError,
)
from src.loan_applications.models import LoanApplicationModel, PropertySpecModel
from src.loan_applications.ports import (
    LoanApplicationQuery,
    LoanApplicationRepositoryPort,
    UserInfoSearchGatewayPort,
)
from src.schemas import PaginatedResponse


class LoanApplicationService:
    def __init__(
        self, repo: LoanApplicationRepositoryPort, users: UserInfoSearchGatewayPort
    ) -> None:
        self._repo = repo
        self._users = users

    async def submit(
        self,
        current_user: CurrentUserModel,
        *,
        broker_id: str | None,
        annual_gross_income: float,
        annual_debt_repayments: float,
        deposit: float,
        term_years: int,
        first_time_buyer: bool,
        property_spec: PropertySpecModel,
    ) -> LoanApplicationModel:
        if broker_id is not None:
            await self._ensure_role(broker_id, UserRole.BROKER)

        # required for the full name copy
        borrower = await self._users.find_user(current_user.uid)

        application = LoanApplicationModel.submit(
            loan_application_id=self._repo.next_id(),
            borrower_id=current_user.uid,
            borrower_full_name=borrower.full_name if borrower else None,
            broker_id=broker_id,
            annual_gross_income=annual_gross_income,
            annual_debt_repayments=annual_debt_repayments,
            deposit=deposit,
            term_years=term_years,
            first_time_buyer=first_time_buyer,
            property_spec=property_spec,
        )
        await self._repo.add_loan_application(application)
        return application

    async def get(
        self, current_user: CurrentUserModel, application_id: str
    ) -> LoanApplicationModel:
        application = await self._repo.get_loan_application(application_id)

        if application is None or not has_view_access(current_user, application):
            raise LoanApplicationNotFoundError(application_id)

        return application

    async def get_all_with_filters(
        self,
        current_user: CurrentUserModel,
        *,
        unclaimed_only: bool = False,
        status: LoanApplicationStatus | None = None,
        ltv_group: LtvGroup | None = None,
        risk_tier: RiskTier | None = None,
        page: int = 1,
        page_size: int = 15,
    ) -> PaginatedResponse[LoanApplicationModel]:
        query = LoanApplicationQuery(
            **self._owner_filter(current_user, unclaimed_only),
            unclaimed_only=unclaimed_only,
            status=status,
            ltv_group=ltv_group,
            risk_tier=risk_tier,
            page=page,
            page_size=page_size,
        )
        return await self._repo.get_loan_applications(query)

    async def claim_by_broker(
        self, current_user: CurrentUserModel, application_id: str
    ) -> LoanApplicationModel:
        return await self._update(
            current_user,
            application_id,
            lambda application: application.claim_by_broker(current_user.uid),
            require_ownership=False,
        )

    async def assign_bank_officer(
        self, current_user: CurrentUserModel, application_id: str, bank_officer_id: str
    ) -> LoanApplicationModel:
        await self._ensure_role(bank_officer_id, UserRole.BANK_OFFICER)

        return await self._update(
            current_user,
            application_id,
            lambda application: application.assign_bank_officer(
                broker_id=current_user.uid, bank_officer_id=bank_officer_id
            ),
        )

    async def release_assignee(
        self, current_user: CurrentUserModel, application_id: str, role: UserRole
    ) -> LoanApplicationModel:
        return await self._update(
            current_user,
            application_id,
            lambda application: application.release_assignee(
                role, released_by_id=current_user.uid
            ),
        )

    async def make_decision(
        self,
        current_user: CurrentUserModel,
        application_id: str,
        *,
        outcome: UnderwritingOutcome,
        reason: str,
        conditions: list[str],
    ) -> LoanApplicationModel:
        return await self._update(
            current_user,
            application_id,
            lambda application: application.make_decision(
                bank_officer_id=current_user.uid,
                outcome=outcome,
                reason=reason,
                conditions=conditions,
            ),
        )

    async def withdraw(
        self, current_user: CurrentUserModel, application_id: str
    ) -> LoanApplicationModel:
        return await self._update(
            current_user,
            application_id,
            lambda application: application.withdraw(current_user.uid),
        )

    async def _update(
        self,
        user: CurrentUserModel,
        application_id: str,
        action: Callable[[LoanApplicationModel], None],
        *,
        require_ownership: bool = True,
    ) -> LoanApplicationModel:
        """Applies `action` ("mutator") to a loan application (i.e., updates it) inside one transaction.

        Args:
            user: user who sent request.
            application_id: ID of the loan application to update.
            action: mutator; change to apply.
            require_ownership: if `True` (default), the caller must be assigned to the loan application;
                use `False` only for claiming an application nobody owns yet.

        Returns:
            LoanApplicationModel: loan application after update.

        Raises:
            LoanApplicationNotFoundError: the application does not exist or the caller has no access.
            LoanApplicationAccessError: the caller can see the application but is not assigned to it.
        """

        def mutator(application: LoanApplicationModel) -> None:
            if not has_view_access(user, application):
                raise LoanApplicationNotFoundError(application_id)

            if require_ownership and not has_modify_access(user, application):
                raise LoanApplicationAccessError(application_id)

            action(application)

        return await self._repo.update_loan_application(application_id, mutator)

    async def _ensure_role(self, uid: str, role: UserRole) -> None:
        """Cheks if the user (referenced in request) exists and has the required role.

        Args:
            uid: user ID
            role: user role

        Raises:
            LoanApplicationInvalidAssigneeError: if the user does not exist or has another role.
        """
        user = await self._users.find_user(uid)

        if user is None or user.role != role:
            raise LoanApplicationInvalidAssigneeError(uid, role)

    @staticmethod
    def _owner_filter(user: CurrentUserModel, unclaimed_only: bool) -> dict[str, str]:
        """Builds mandatory filter that limits a list to the caller's related loan applications.

        Args:
            user: user who sent request.
            unclaimed_only: `True` if a broker asks for the shared pool of unclaimed applications.

        Returns:
            dict[str, str]: one `LoanApplicationQuery` field with the caller's uid: `borrower_id`, `broker_id`, or `bank_officer_id`;
            empty if unclaimed_only is `True` and user is a broker.

        Raises:
            ValueError: if unexpected role is provided.
        """
        if user.role == UserRole.BROKER and unclaimed_only:
            return {}

        assignee_field = (
            ASSIGNEE_FIELD.get(user.role) if user.role is not None else None
        )
        if assignee_field is None:
            raise ValueError("Unexpected role passed")

        return {assignee_field: user.uid}
