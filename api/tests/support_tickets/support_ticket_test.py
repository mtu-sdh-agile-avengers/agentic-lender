"""ALG4-218: POST /api/v1/support-tickets."""

import asyncio

import pytest

from src.support_tickets.dependencies import get_support_ticket_service
from src.support_tickets.enums import SupportTicketCategory, SupportTicketStatus
from src.support_tickets.exceptions import SupportTicketLoanApplicationError
from src.support_tickets.service import SupportTicketService
from tests import fakes

URL = "/api/v1/support-tickets"


def make_service() -> tuple[SupportTicketService, fakes.FakeStore]:
    store = fakes.FakeStore()
    return SupportTicketService(
        store, fakes.FakeApplications(fakes.application())
    ), store


def test_ticket_about_own_application_is_saved_open():
    service, store = make_service()
    ticket = asyncio.run(
        service.submit(
            fakes.user(fakes.BORROWER),
            category=SupportTicketCategory.LOAN_APPLICATION,
            description="I uploaded the wrong payslip",
            loan_application_id="app-1",
        )
    )
    assert ticket.status is SupportTicketStatus.OPEN
    assert ticket.user_id == fakes.BORROWER
    assert store.saved == [ticket]


def test_ticket_about_someone_elses_application_is_404():
    service, store = make_service()
    for app_id in ("app-1", "missing"):
        with pytest.raises(SupportTicketLoanApplicationError):
            asyncio.run(
                service.submit(
                    fakes.user(fakes.OTHER_BORROWER),
                    category=SupportTicketCategory.LOAN_APPLICATION,
                    description="Where is my application?",
                    loan_application_id=app_id,
                )
            )
    assert store.saved == []


def client(uid: str = fakes.BORROWER):
    service, _ = make_service()
    return fakes.client_as(uid, {get_support_ticket_service: lambda: service})


def test_route_creates_ticket():
    with client() as c:
        response = c.post(
            URL,
            json={
                "category": "technical",
                "description": "  The app crashes on upload  ",
            },
        )
    assert response.status_code == 201
    body = response.json()
    assert body["description"] == "The app crashes on upload"
    assert body["status"] == "open"
    assert body["loanApplicationId"] is None
    assert body["supportTicketId"] == "id-1"


@pytest.mark.parametrize(
    "payload",
    [
        {"category": "loan_application", "description": "Help"},  # application missing
        {
            "category": "payment",
            "description": "Help",
            "loanApplicationId": "app-1",
        },  # not for this category
        {"category": "other", "description": "   "},  # blank
        {"category": "other", "description": "x" * 1001},  # too long
        {"category": "complaint", "description": "Help"},  # unknown category
    ],
)
def test_route_rejects_invalid_body(payload):
    with client() as c:
        assert c.post(URL, json=payload).status_code == 422


def test_only_borrowers_submit_tickets():
    with client(fakes.BROKER) as c:
        assert (
            c.post(URL, json={"category": "other", "description": "Hi"}).status_code
            == 403
        )
