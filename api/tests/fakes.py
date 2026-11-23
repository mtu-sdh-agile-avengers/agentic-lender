"""In-memory stand-ins for the Firestore repositories, plus a decided sample application (no network)."""

import datetime
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from fastapi.testclient import TestClient

from src.assessments.enums import AIDecision, AssessmentStatus
from src.assessments.models import (
    AgentStepModel,
    AssessmentModel,
    DecisionModel,
    VoteModel,
)
from src.auth.dependencies import get_current_user
from src.auth.enums import SignInProvider, UserRole
from src.auth.models import CurrentUserModel
from src.loan_applications.enums import (
    BerRating,
    County,
    PropertyType,
    RiskTier,
    UnderwritingOutcome,
)
from src.loan_applications.models import (
    LoanApplicationModel,
    LoanDocumentModel,
    PropertySpecModel,
    UserInfoModel,
)
from src.main import app

BORROWER = "uid-borrower"
OTHER_BORROWER = "uid-other-borrower"
BROKER = "uid-broker"
OFFICER = "uid-officer"
OTHER_OFFICER = "uid-other-officer"

ROLES = {
    BORROWER: UserRole.BORROWER,
    OTHER_BORROWER: UserRole.BORROWER,
    BROKER: UserRole.BROKER,
    OFFICER: UserRole.BANK_OFFICER,
    OTHER_OFFICER: UserRole.BANK_OFFICER,
}


def user(uid: str) -> CurrentUserModel:
    return CurrentUserModel(
        uid=uid,
        email=f"{uid}@demo.agenticlender.ie",
        sign_in_provider=SignInProvider.PASSWORD_EMAIL,
        role=ROLES[uid],
    )


def application(
    *, decided: bool = False, assessed: bool = True
) -> LoanApplicationModel:
    """An application of BORROWER, claimed by BROKER and assigned to OFFICER; optionally assessed and approved."""
    app = LoanApplicationModel.submit(
        loan_application_id="app-1",
        borrower_id=BORROWER,
        borrower_full_name="Bríd Borrower",
        annual_gross_income=85_000,
        annual_debt_repayments=2_400,
        deposit=50_000,
        term_years=30,
        first_time_buyer=True,
        property_spec=PropertySpecModel(
            county=County.CORK,
            address="12 Main Street, Cork",
            floor_area_m2=110,
            bedrooms=3,
            bathrooms=2,
            property_type=PropertyType.SEMI_D,
            ber=BerRating.B2,
            asking_price=350_000,
        ),
    )
    app.claim_by_broker(BROKER)
    app.assign_bank_officer(broker_id=BROKER, bank_officer_id=OFFICER)
    if assessed or decided:
        app.start_assessment(assessment_id="assessment-1")
        app.finish_assessment(assessment_id="assessment-1", risk_tier=RiskTier.LOW)
    if decided:
        app.make_decision(
            bank_officer_id=OFFICER,
            outcome=UnderwritingOutcome.APPROVED,
            reason="Affordable with a healthy margin.",
            conditions=["Final payslip before drawdown"],
        )
    return app


def assessment() -> AssessmentModel:
    return AssessmentModel(
        assessment_id="assessment-1",
        loan_application_id="app-1",
        requested_by_id=BROKER,
        job_id="job-1",
        status=AssessmentStatus.DONE,
        rate_percent=3.9,
        affordability={
            "monthly_repayment": 1415,
            "stressed_repayment": 1590,
            "dti_percent": 25.3,
            "lti_multiple": 3.53,
            "breaches": [],
        },
        collateral={
            "estimate": 352_000,
            "asking_price": 350_000,
            "gap_percent": -0.6,
            "overvalued": False,
            "ltv_percent": 85.7,
            "model_version": "v1",
        },
        decision=DecisionModel(
            decision=AIDecision.APPROVE,
            reason="Stressed DTI well under the limit.",
            key_risks=["High LTV"],
            votes=[
                VoteModel(
                    provider="groq", decision=AIDecision.APPROVE, reason="Affordable"
                ),
                VoteModel(provider="gemini", decision=None, reason=None),
            ],
        ),
        risk={"tier": "Low", "score": 22, "approval_chance_percent": 96},
        created_at=datetime.datetime(2026, 11, 2, 9, 0, tzinfo=datetime.UTC),
        finished_at=datetime.datetime(2026, 11, 2, 9, 1, tzinfo=datetime.UTC),
    )


STEPS = [
    AgentStepModel(step_number=2, agent="valuation", summary="Estimate €352,000"),
    AgentStepModel(step_number=1, agent="affordability", summary="Stressed DTI 25.3%"),
]


class FakeApplications:
    """`LoanApplicationRepositoryPort` over a dict."""

    def __init__(
        self,
        *apps: LoanApplicationModel,
        documents: list[LoanDocumentModel] | None = None,
    ) -> None:
        self.apps = {app.loan_application_id: app for app in apps}
        self.documents = documents or []

    def next_id(self) -> str:
        return f"app-{len(self.apps) + 1}"

    async def get_loan_application(
        self, application_id: str
    ) -> LoanApplicationModel | None:
        return self.apps.get(application_id)

    async def get_documents(self, application_id: str) -> list[LoanDocumentModel]:
        return list(self.documents) if application_id in self.apps else []

    async def update_loan_application(
        self, application_id: str, mutator: Callable[[LoanApplicationModel], None]
    ) -> LoanApplicationModel:
        app = self.apps[application_id]
        mutator(app)
        return app


class FakeUsers:
    """`UserInfoSearchGatewayPort`: only the borrower has a profile."""

    async def find_user(self, uid: str) -> UserInfoModel | None:
        if uid != BORROWER:
            return None
        return UserInfoModel(
            uid=BORROWER,
            full_name="Bríd Borrower",
            role=UserRole.BORROWER,
            email="brid@example.ie",
            phone="+353871234567",
        )


class FakeAssessments:
    def __init__(
        self, *items: AssessmentModel, steps: list[AgentStepModel] | None = None
    ) -> None:
        self.items = {(a.loan_application_id, a.assessment_id): a for a in items}
        self.steps = steps or []

    async def get_assessment(
        self, loan_application_id: str, assessment_id: str
    ) -> AssessmentModel | None:
        return self.items.get((loan_application_id, assessment_id))

    async def get_agent_steps(
        self, loan_application_id: str, assessment_id: str
    ) -> list[AgentStepModel]:
        return list(self.steps)


class FakeStore:
    """`next_id` + `add_*` of a write-only collection (support tickets, reviews)."""

    def __init__(self) -> None:
        self.saved: list[Any] = []

    def next_id(self) -> str:
        return f"id-{len(self.saved) + 1}"

    async def add_support_ticket(self, ticket) -> None:
        self.saved.append(ticket)

    async def add_review(self, review) -> None:
        self.saved.append(review)


@contextmanager
def client_as(uid: str, overrides: dict[Callable, Callable]) -> Iterator[TestClient]:
    """TestClient where `uid` is signed in and services use the fakes above (no Firebase, no Firestore)."""
    app.dependency_overrides[get_current_user] = lambda: user(uid)
    app.dependency_overrides.update(overrides)
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
