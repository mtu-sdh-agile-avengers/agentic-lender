from src.auth.models import CurrentUserModel
from src.loan_applications.access import ASSIGNEE_FIELD, has_modify_access
from src.loan_applications.calculations import OFFERED_RATE_PERCENT
from src.loan_applications.enums import LoanApplicationStatus
from src.loan_applications.models import LoanApplicationModel
from src.loan_applications.ports import LoanApplicationRepositoryPort
from src.stress_tests.calculations import DTI_LIMIT_PERCENT, stress_portfolio
from src.stress_tests.exceptions import (
    StressTestEmptyPortfolioError,
    StressTestNotFoundError,
)
from src.stress_tests.models import StressTestModel
from src.stress_tests.ports import StressTestRepositoryPort

# keeps one stress test document well below the Firestore limit of 1 MiB
MAX_PORTFOLIO_SIZE = 300

# by default every application that is not closed yet
DEFAULT_STATUSES: frozenset[LoanApplicationStatus] = frozenset(
    LoanApplicationStatus
) - {LoanApplicationStatus.CLOSED}


class StressTestService:
    def __init__(
        self,
        applications: LoanApplicationRepositoryPort,
        stress_tests: StressTestRepositoryPort,
    ) -> None:
        self._applications = applications
        self._stress_tests = stress_tests

    async def run(
        self,
        current_user: CurrentUserModel,
        *,
        rate_shock_bps: int,
        price_change_percent: float,
        statuses: set[LoanApplicationStatus] | None = None,
        loan_application_ids: list[str] | None = None,
    ) -> StressTestModel:
        """Stresses the user's portfolio and saves the run.

        The portfolio is the user's own applications (`broker_id` or `bank_officer_id` holds their uid):
        the ones listed in `loan_application_ids`, otherwise all of them with one of `statuses`.

        Args:
            current_user: mortgage broker or underwriting bank officer.
            rate_shock_bps: interest rate rise in basis points (`0` or `100`..`300`).
            price_change_percent: property value change in % (`0` or negative).
            statuses: portfolio filter; every status except `Closed` by default. Ignored with `loan_application_ids`.
            loan_application_ids: concrete applications to stress; applications of other users are skipped.

        Returns:
            StressTestModel: the saved run; `results` are ordered with the borrowers hit hardest first.

        Raises:
            StressTestEmptyPortfolioError: if the selection contains none of the user's applications.
        """
        statuses = set(statuses or DEFAULT_STATUSES)
        portfolio = await self._portfolio(current_user, statuses, loan_application_ids)
        if not portfolio:
            raise StressTestEmptyPortfolioError

        stress_test = StressTestModel(
            stress_test_id=self._stress_tests.next_id(),
            user_id=current_user.uid,
            statuses=sorted(statuses),
            loan_application_ids=loan_application_ids,
            rate_shock_bps=rate_shock_bps,
            price_change_percent=price_change_percent,
            base_rate_percent=OFFERED_RATE_PERCENT,
            dti_limit_percent=DTI_LIMIT_PERCENT,
            results=stress_portfolio(
                portfolio,
                rate_shock_bps=rate_shock_bps,
                price_change_percent=price_change_percent,
                base_rate_percent=OFFERED_RATE_PERCENT,
                dti_limit_percent=DTI_LIMIT_PERCENT,
            ),
        )
        await self._stress_tests.add_stress_test(stress_test)
        return stress_test

    async def get(
        self, current_user: CurrentUserModel, stress_test_id: str
    ) -> StressTestModel:
        """Returns one of the user's stress tests.

        Raises:
            StressTestNotFoundError: if it does not exist or was run by another user.
        """
        stress_test = await self._stress_tests.get_stress_test(stress_test_id)
        if stress_test is None or stress_test.user_id != current_user.uid:
            raise StressTestNotFoundError(stress_test_id)
        return stress_test

    async def get_mine(
        self, current_user: CurrentUserModel, limit: int = 20
    ) -> list[StressTestModel]:
        """Returns the user's latest stress tests, newest first."""
        return await self._stress_tests.get_stress_tests(current_user.uid, limit)

    async def _portfolio(
        self,
        current_user: CurrentUserModel,
        statuses: set[LoanApplicationStatus],
        loan_application_ids: list[str] | None,
    ) -> list[LoanApplicationModel]:
        if loan_application_ids:
            found = await self._applications.get_loan_applications_by_ids(
                loan_application_ids[:MAX_PORTFOLIO_SIZE]
            )
            return [
                app for app in found.values() if has_modify_access(current_user, app)
            ]

        field = ASSIGNEE_FIELD.get(current_user.role) if current_user.role else None
        if field not in ("broker_id", "bank_officer_id"):
            return []

        return await self._applications.get_portfolio(
            statuses=statuses,
            limit=MAX_PORTFOLIO_SIZE,
            **{field: current_user.uid},
        )
