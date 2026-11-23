"""ALG4-255: GET /api/v1/loan-applications/{id} returns the loan file (dossier)."""

import asyncio
import datetime

import pytest

from src.loan_applications.dependencies import get_loan_application_service
from src.loan_applications.exceptions import (
    LoanApplicationAccessError,
    LoanApplicationNotFoundError,
)
from src.loan_applications.models import LoanDocumentModel
from src.loan_applications.service import LoanApplicationService
from tests import fakes

DOCUMENTS = [
    LoanDocumentModel(
        document_id="doc-2",
        name="Bank statement.pdf",
        content_type="application/pdf",
        uploaded_at=datetime.datetime(2026, 11, 3, tzinfo=datetime.UTC),
    ),
    LoanDocumentModel(
        document_id="doc-1",
        name="Payslip.pdf",
        storage_path="loan-files/app-1/payslip.pdf",
        uploaded_at=datetime.datetime(2026, 11, 1, tzinfo=datetime.UTC),
    ),
]


def service(assessed: bool = True) -> LoanApplicationService:
    return LoanApplicationService(
        fakes.FakeApplications(
            fakes.application(assessed=assessed), documents=DOCUMENTS
        ),
        fakes.FakeUsers(),
        fakes.FakeAssessments(fakes.assessment()),
    )


def test_assigned_officer_gets_the_full_file():
    view = asyncio.run(service().get_file(fakes.user(fakes.OFFICER), "app-1"))
    assert view.borrower.email == "brid@example.ie"
    assert [d.document_id for d in view.documents] == ["doc-2", "doc-1"]
    assert view.latest_assessment.assessment_id == "assessment-1"


def test_borrower_and_broker_see_their_application():
    for uid in (fakes.BORROWER, fakes.BROKER):
        view = asyncio.run(service().get_file(fakes.user(uid), "app-1"))
        assert view.application.loan_application_id == "app-1"


def test_someone_elses_application_is_403_and_a_missing_one_404():
    for uid in (fakes.OTHER_OFFICER, fakes.OTHER_BORROWER):
        with pytest.raises(LoanApplicationAccessError):
            asyncio.run(service().get_file(fakes.user(uid), "app-1"))
    with pytest.raises(LoanApplicationNotFoundError):
        asyncio.run(service().get_file(fakes.user(fakes.OFFICER), "missing"))


def test_not_assessed_application_has_no_summary():
    view = asyncio.run(
        service(assessed=False).get_file(fakes.user(fakes.OFFICER), "app-1")
    )
    assert view.latest_assessment is None


def test_route_returns_the_dossier_in_camel_case():
    overrides = {get_loan_application_service: service}
    with fakes.client_as(fakes.OFFICER, overrides) as client:
        body = client.get("/api/v1/loan-applications/app-1").json()

    assert body["loanApplicationId"] == "app-1"
    assert body["borrower"] == {
        "uid": fakes.BORROWER,
        "fullName": "Bríd Borrower",
        "email": "brid@example.ie",
        "phone": "+353871234567",
    }
    assert body["documents"][1]["name"] == "Payslip.pdf"
    assert (
        "storagePath" not in body["documents"][1]
    )  # internal: where the file lives in Cloud Storage
    summary = body["latestAssessment"]
    assert summary["decision"] == "Approve"
    assert summary["riskTier"] == "Low"
    assert summary["approvalChancePercent"] == 96
    assert summary["dtiPercent"] == 25.3
    assert summary["valuationEstimate"] == 352_000
    assert body["statusHistory"][0]["status"] == "Applied"


def test_route_status_codes():
    overrides = {get_loan_application_service: service}
    with fakes.client_as(fakes.OTHER_OFFICER, overrides) as client:
        assert client.get("/api/v1/loan-applications/app-1").status_code == 403
        assert client.get("/api/v1/loan-applications/missing").status_code == 404
