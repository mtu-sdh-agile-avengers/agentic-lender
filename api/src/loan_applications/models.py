import datetime
from typing import Self, ClassVar

from pydantic import BaseModel, Field

from src.auth.enums import UserRole
from src.utils import _get_utc_now
from src.loan_applications import calculations
from src.loan_applications.enums import (
    County,
    PropertyType,
    BerRating,
    UnderwritingOutcome,
    LtvGroup,
    LoanApplicationStatus,
    RiskTier,
)
from src.loan_applications.exceptions import (
    LoanApplicationStatusChangeError,
    LoanApplicationIsNotOpenError,
    LoanApplicationAssigneeAlreadySetError,
    LoanApplicationAccessError,
)


class UserInfoModel(BaseModel):
    uid: str
    full_name: str | None
    role: UserRole


class PropertySpecModel(BaseModel):
    """Property Specification related to Loan Application (`loan_applications.property_spec`)."""

    county: County
    address: str | None = None
    floor_area_m2: float
    bedrooms: int
    bathrooms: int
    property_type: PropertyType
    ber: BerRating | None = None
    latitude: float | None = None
    longitude: float | None = None
    asking_price: float


class LoanApplicationStatusChangeModel(BaseModel):
    """Status change related to `loan_applications.status_history`."""

    status: LoanApplicationStatus
    changed_by_id: str
    changed_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


class UnderwritingDecisionModel(BaseModel):
    """Final decision of the underwriting bank officer (`loan_applications.decision`)."""

    outcome: UnderwritingOutcome
    reason: str
    conditions: list[str]
    decided_by: str
    decided_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


class LoanApplicationModel(BaseModel):
    # state machine of allowed status transitions: from initial status -> to the list of allowed once
    _ALLOWED_TRANSITIONS: ClassVar[
        dict[LoanApplicationStatus, frozenset[LoanApplicationStatus]]
    ] = {
        LoanApplicationStatus.APPLIED: frozenset(
            {LoanApplicationStatus.AI_DELIBERATED, LoanApplicationStatus.CLOSED}
        ),
        LoanApplicationStatus.AI_DELIBERATED: frozenset(
            {LoanApplicationStatus.UNDERWRITER_APPROVED, LoanApplicationStatus.CLOSED}
        ),
        LoanApplicationStatus.UNDERWRITER_APPROVED: frozenset(
            {LoanApplicationStatus.FUNDED, LoanApplicationStatus.CLOSED}
        ),
        LoanApplicationStatus.FUNDED: frozenset({LoanApplicationStatus.CLOSED}),
        LoanApplicationStatus.CLOSED: frozenset(),
    }

    # set of statuses on which related broker and underwriting could be changed
    _OPEN_STATUSES: ClassVar[frozenset[LoanApplicationStatus]] = frozenset(
        {LoanApplicationStatus.APPLIED, LoanApplicationStatus.AI_DELIBERATED}
    )

    SYSTEM_ACTOR_ID: ClassVar[str] = "system"

    loan_application_id: str
    borrower_id: str
    borrower_full_name: str | None = None
    broker_id: str | None = None
    bank_officer_id: str | None = None

    annual_gross_income: float
    annual_debt_repayments: float
    deposit: float
    loan_amount: float
    term_years: int
    first_time_buyer: bool
    ltv: float
    ltv_group: LtvGroup

    property_spec: PropertySpecModel

    status: LoanApplicationStatus = LoanApplicationStatus.APPLIED
    status_history: list[LoanApplicationStatusChangeModel] = Field(default_factory=list)

    assessment_id: str | None = None
    risk_tier: RiskTier | None = None

    decision: UnderwritingDecisionModel | None = None

    created_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    updated_at: datetime.datetime = Field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )

    @classmethod
    def submit(
        cls,
        *,
        loan_application_id: str,
        borrower_id: str,
        borrower_full_name: str | None,
        broker_id: str | None = None,
        annual_gross_income: float,
        annual_debt_repayments: float,
        deposit: float,
        term_years: int,
        first_time_buyer: bool,
        property_spec: PropertySpecModel,
    ) -> Self:
        loan_amount = calculations.loan_amount(property_spec.asking_price, deposit)
        ltv = calculations.loan_to_value(loan_amount, property_spec.asking_price)
        now = _get_utc_now()

        return cls(
            loan_application_id=loan_application_id,
            borrower_id=borrower_id,
            borrower_full_name=borrower_full_name,
            broker_id=broker_id,
            annual_gross_income=annual_gross_income,
            annual_debt_repayments=annual_debt_repayments,
            deposit=deposit,
            loan_amount=loan_amount,
            term_years=term_years,
            first_time_buyer=first_time_buyer,
            ltv=ltv,
            ltv_group=calculations.ltv_group(ltv),
            property_spec=property_spec,
            status=LoanApplicationStatus.APPLIED,
            status_history=[
                LoanApplicationStatusChangeModel(
                    status=LoanApplicationStatus.APPLIED,
                    changed_by_id=borrower_id,
                    changed_at=now,
                )
            ],
            created_at=now,
            updated_at=now,
        )

    def claim_by_broker(self, broker_id: str) -> None:
        """Claims a loan application to specified mortgage broker.

        Raises:
            LoanApplicationAlreadySetError: if application already have related broker.
            LoanApplicationStatusIsNotOpenError: if the loan application status is not in `_OPEN_STATUSES`.
        """
        if self.broker_id == broker_id:
            return  # idempotent

        if self.broker_id is not None:
            raise LoanApplicationAssigneeAlreadySetError(
                self.loan_application_id, UserRole.BROKER
            )

        self._ensure_open()

        self.broker_id = broker_id
        self.updated_at = _get_utc_now()

    def assign_bank_officer(
        self,
        *,
        broker_id: str,
        bank_officer_id: str,
    ) -> None:
        """Assigns a bank officer to the loan application.

        Raises:
            LoanApplicationAccessError: caller is not the assigned broker.
            LoanApplicationStatusIsNotOpenError: if the loan application status is not in `_OPEN_STATUSES`.
        """
        self._ensure_assignee(self.broker_id, broker_id)
        self._ensure_open()

        if self.bank_officer_id == bank_officer_id:
            return  # idempotent

        self.bank_officer_id = bank_officer_id
        self.updated_at = _get_utc_now()

    def release_assignee(self, role: UserRole, *, released_by_id: str):
        """Removes the assigned mortgage broker or underwriting bank officer from the loan application.

        Raises:

        """
        match role:
            case UserRole.BROKER:
                if self.broker_id is None:
                    return  # idempotent

                self._ensure_assignee(self.broker_id, released_by_id)
                self._ensure_open()

                if self.bank_officer_id is not None:
                    raise LoanApplicationAssigneeAlreadySetError(
                        self.loan_application_id, UserRole.BANK_OFFICER
                    )

                self.broker_id = None

            case UserRole.BANK_OFFICER:
                if self.bank_officer_id is None:
                    return  # idempotent

                if released_by_id not in (self.broker_id, self.bank_officer_id):
                    raise LoanApplicationAccessError(self.loan_application_id)

                self._ensure_open()

                self.bank_officer_id = None

            case _:
                raise ValueError(
                    f"Role {role} is not valid or cannot be released from an application"
                )

        self.updated_at = _get_utc_now()

    def change_status_to(
        self,
        new_status: LoanApplicationStatus,
        *,
        changed_by_id: str,
        at: datetime.datetime | None = None,
    ) -> None:
        """Changes status of the loan application to `new_status` if it's allowed by `_ALLOWED_TRANSITIONS`.

        Raises:
            LoanApplicationStatusChangeError: if transition is not allowed.
        """
        if new_status not in self._ALLOWED_TRANSITIONS[self.status]:
            raise LoanApplicationStatusChangeError(self.status, new_status)

        now = at or _get_utc_now()
        self.status = new_status
        self.status_history.append(
            LoanApplicationStatusChangeModel(
                status=new_status, changed_by_id=changed_by_id, changed_at=now
            )
        )
        self.updated_at = now

    def start_assessment(
        self,
        *,
        assessment_id: str,
    ) -> None:
        """Starts new AI committee run."""
        self._ensure_open()

        self.assessment_id = assessment_id
        self.updated_at = _get_utc_now()

    def finish_assessment(
        self, *, assessment_id: str, risk_tier: RiskTier | None = None
    ) -> bool:
        """Saves a finished (last) AI committee run and changes application status to `AI Deliberated` on the first call

        Returns:
            True if the result was applied, False otherwise (if ignored).
        """
        if assessment_id != self.assessment_id:
            return False  # required to ignore the old run of AI committee job

        if self.status not in self._OPEN_STATUSES:
            return False  # withdrawn / already decided while AI comittee running

        now = _get_utc_now()
        self.risk_tier = risk_tier

        if self.status == LoanApplicationStatus.APPLIED:
            self.change_status_to(
                LoanApplicationStatus.AI_DELIBERATED,
                changed_by_id=self.SYSTEM_ACTOR_ID,
                at=now,
            )
        else:
            self.updated_at = now

        return True

    def make_decision(
        self,
        *,
        bank_officer_id: str,
        outcome: UnderwritingOutcome,
        reason: str,
        conditions: list[str],
    ) -> None:
        """Makes final decision for the loan application (on behalf of underwriting bank officer).

        Raises:
            LoanApplicationAccessError: if caller is not the assigned bank officer.
            LoanApplicationStatusChangeError: if application is not `AI Deliberated` yet
        """
        self._ensure_assignee(self.bank_officer_id, bank_officer_id)

        new_status = (
            LoanApplicationStatus.UNDERWRITER_APPROVED
            if outcome == UnderwritingOutcome.APPROVED
            else LoanApplicationStatus.CLOSED
        )

        if self.status != LoanApplicationStatus.AI_DELIBERATED:
            raise LoanApplicationStatusChangeError(self.status, new_status)

        now = _get_utc_now()
        self.decision = UnderwritingDecisionModel(
            outcome=outcome,
            reason=reason,
            conditions=conditions,
            decided_by=bank_officer_id,
            decided_at=now,
        )
        self.change_status_to(new_status, changed_by_id=bank_officer_id, at=now)

    def withdraw(self, borrower_id: str) -> None:
        """Withdraws (cancels) current loan application before a decision is made (CLOSED).

        Raises:
            LoanApplicationAccessError: if caller is not the assigned borrower.
            LoanApplicationStatusChangeError: if the loan application status is not in `_OPEN_STATUSES`.
        """
        self._ensure_assignee(self.borrower_id, borrower_id)
        self._ensure_open()

        self.change_status_to(LoanApplicationStatus.CLOSED, changed_by_id=borrower_id)

    def _ensure_open(self) -> None:
        """Ensures that the loan application is open (i.e., assignees such as: mortgage broker
        and underwriting bank officer could change).

        Raises:
            LoanApplicationStatusChangeError: if the loan application status is not in `_OPEN_STATUSES`.
        """
        if self.status not in self._OPEN_STATUSES:
            raise LoanApplicationIsNotOpenError(self.status)

    def _ensure_assignee(self, assignee_id: str | None, passed_id: str) -> None:
        """Ensures that passed user id is a real assignee (mortgage broker / underwriting bank officer).

        Raises:
            LoanApplicationAccessError: if `passed_id` is not a real assignee.
        """
        if assignee_id != passed_id:
            raise LoanApplicationAccessError(self.loan_application_id)
