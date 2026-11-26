"""ALG4-227 (start a payment), ALG4-228 (Stripe webhook) and ALG4-232 (history)."""

import asyncio
import datetime
import hashlib
import hmac
import json
import time
from typing import Any

import pytest

from src.loan_applications.exceptions import LoanApplicationNotFoundError
from src.payments.dependencies import get_payment_service
from src.payments.enums import PaymentFeeType, PaymentStatus
from src.payments.exceptions import (
    PaymentAlreadyPaidError,
    PaymentApplicationClosedError,
    PaymentNotFoundError,
    PaymentsNotConfiguredError,
)
from src.payments.gateway import StripeGateway, StripeIntent
from src.payments.models import PaymentModel
from src.payments.service import PaymentService
from tests import fakes

WEBHOOK_SECRET = "whsec_test_secret"
VERIFY = PaymentFeeType.APPLICATION_VERIFICATION
FAST_TRACK = PaymentFeeType.APPRAISAL_PROCESSING


class FakePayments:
    """`PaymentRepositoryPort` over a dict."""

    def __init__(self, *payments: PaymentModel) -> None:
        self.items = {p.payment_id: p for p in payments}
        self.counter = 0

    def next_id(self) -> str:
        self.counter += 1
        return f"pay-{self.counter}"

    async def add_payment(self, payment: PaymentModel) -> None:
        self.items[payment.payment_id] = payment

    async def get_payment(self, payment_id: str) -> PaymentModel | None:
        return self.items.get(payment_id)

    async def update_payment(self, payment_id: str, fields: dict[str, Any]) -> None:
        self.items[payment_id] = self.items[payment_id].model_copy(update=fields)

    async def get_user_payments(self, user_id: str) -> list[PaymentModel]:
        return [p for p in self.items.values() if p.user_id == user_id]

    async def find_by_provider_id(
        self, payment_provider_id: str
    ) -> PaymentModel | None:
        return next(
            (
                p
                for p in self.items.values()
                if p.payment_provider_id == payment_provider_id
            ),
            None,
        )


class FakeGateway:
    """Stripe stand-in: PaymentIntents in a dict; webhook signatures checked by the real gateway code."""

    def __init__(self, configured: bool = True) -> None:
        self.publishable_key = "pk_test_123"
        self._configured = configured
        self.intents: dict[str, StripeIntent] = {}
        self.created: list[dict] = []
        self._verifier = StripeGateway("", "", WEBHOOK_SECRET)

    @property
    def configured(self) -> bool:
        return self._configured

    async def create_payment_intent(
        self, *, payment_id, amount_cents, currency, description, metadata
    ):
        self.created.append(
            {
                "payment_id": payment_id,
                "amount": amount_cents,
                "currency": currency,
                "metadata": metadata,
            }
        )
        intent = StripeIntent(
            f"pi_{payment_id}",
            f"pi_{payment_id}_secret",
            "requires_payment_method",
            amount_cents,
            currency,
        )
        self.intents[intent.id] = intent
        return intent

    async def retrieve_payment_intent(self, payment_intent_id):
        return self.intents[payment_intent_id]

    def parse_webhook(self, payload, signature):
        return self._verifier.parse_webhook(payload, signature)


def make(*payments: PaymentModel, status: str = "Applied", configured: bool = True):
    app = fakes.application(assessed=False)
    app.status = status
    repo, gateway = FakePayments(*payments), FakeGateway(configured)
    return PaymentService(repo, fakes.FakeApplications(app), gateway), repo, gateway


def start(service, uid=fakes.BORROWER, fee=FAST_TRACK, app_id="app-1"):
    return asyncio.run(
        service.start(fakes.user(uid), loan_application_id=app_id, fee_type=fee)
    )


def payment(
    pid: str,
    status: PaymentStatus,
    *,
    fee=FAST_TRACK,
    provider_id: str | None = None,
    minutes: int = 0,
):
    return PaymentModel(
        payment_id=pid,
        user_id=fakes.BORROWER,
        loan_application_id="app-1",
        fee_type=fee,
        amount=149.0 if fee == FAST_TRACK else 49.0,
        payment_provider_id=provider_id,
        status=status,
        created_at=datetime.datetime(2026, 11, 24, 10, minutes, tzinfo=datetime.UTC),
    )


# --- ALG4-227 --------------------------------------------------------------------------------------------------


def test_new_payment_gets_a_payment_intent_for_the_fee():
    service, repo, gateway = make()
    checkout = start(service)
    assert checkout.created
    assert (
        checkout.payment.status is PaymentStatus.PENDING
        and checkout.payment.amount == 149.0
    )
    assert checkout.intent.client_secret == "pi_pay-1_secret"
    assert checkout.publishable_key == "pk_test_123"
    assert gateway.created == [
        {
            "payment_id": "pay-1",
            "amount": 14900,
            "currency": "eur",
            "metadata": {
                "loan_application_id": "app-1",
                "fee_type": "appraisal_processing",
                "user_id": fakes.BORROWER,
            },
        }
    ]
    assert (
        repo.items["pay-1"].payment_provider_id == "pi_pay-1"
    )  # stored to match webhook events


def test_retry_reuses_the_unpaid_payment():
    service, repo, gateway = make()
    first = start(service)
    again = start(service)
    assert not again.created and again.payment.payment_id == first.payment.payment_id
    assert len(gateway.created) == 1 and len(repo.items) == 1

    repo.items["pay-1"] = repo.items["pay-1"].model_copy(
        update={"status": PaymentStatus.FAILED, "failure_reason": "declined"}
    )
    retry = start(service)
    assert (
        retry.payment.status is PaymentStatus.PENDING
        and repo.items["pay-1"].failure_reason is None
    )

    other_fee = start(service, fee=VERIFY)
    assert other_fee.created and other_fee.payment.amount == 49.0


def test_payment_left_without_intent_is_finished_and_canceled_intent_replaced():
    service, repo, gateway = make(
        payment("pay-old", PaymentStatus.PENDING)
    )  # Stripe failed last time
    checkout = start(service)
    assert not checkout.created and checkout.payment.payment_id == "pay-old"
    assert repo.items["pay-old"].payment_provider_id == "pi_pay-old"

    gateway.intents["pi_pay-old"] = StripeIntent(
        "pi_pay-old", "s", "canceled", 14900, "eur"
    )
    assert start(service).created  # a canceled intent cannot be paid: a new payment


def test_rules():
    service, _repo, _gateway = make(
        payment("paid", PaymentStatus.SUCCEEDED, provider_id="pi_paid")
    )
    with pytest.raises(PaymentAlreadyPaidError):
        start(service)
    with pytest.raises(LoanApplicationNotFoundError):
        start(service, uid=fakes.OTHER_BORROWER)
    with pytest.raises(LoanApplicationNotFoundError):
        start(service, app_id="missing")
    with pytest.raises(PaymentApplicationClosedError):
        start(make(status="Closed")[0])
    with pytest.raises(PaymentsNotConfiguredError):
        start(make(configured=False)[0])


def test_missed_webhook_is_caught_up_on_retry():
    service, repo, gateway = make(
        payment("pay-1", PaymentStatus.PENDING, provider_id="pi_x")
    )
    gateway.intents["pi_x"] = StripeIntent("pi_x", "s", "succeeded", 14900, "eur")
    with pytest.raises(PaymentAlreadyPaidError):
        start(service)
    assert repo.items["pay-1"].status is PaymentStatus.SUCCEEDED


# --- ALG4-232 --------------------------------------------------------------------------------------------------


def test_history_is_the_borrowers_newest_first():
    stranger = payment("theirs", PaymentStatus.SUCCEEDED).model_copy(
        update={"user_id": fakes.OTHER_BORROWER}
    )
    other_app = payment("elsewhere", PaymentStatus.PENDING, minutes=5).model_copy(
        update={"loan_application_id": "app-9"}
    )
    service, _, _ = make(
        payment("old", PaymentStatus.FAILED, fee=VERIFY, minutes=1),
        payment("new", PaymentStatus.SUCCEEDED, minutes=9),
        stranger,
        other_app,
    )
    me = fakes.user(fakes.BORROWER)
    page = asyncio.run(service.get_history(me))
    assert [p.payment_id for p in page.items] == ["new", "elsewhere", "old"]
    only_app = asyncio.run(
        service.get_history(me, loan_application_id="app-1", page=1, page_size=1)
    )
    assert (
        [p.payment_id for p in only_app.items],
        only_app.total,
        only_app.has_next,
    ) == (["new"], 2, True)

    assert asyncio.run(service.get(me, "new")).payment_id == "new"
    with pytest.raises(PaymentNotFoundError):
        asyncio.run(service.get(me, "theirs"))


# --- ALG4-228 --------------------------------------------------------------------------------------------------


def event(kind: str, obj: dict, created: int = 1795514442) -> dict:
    return {
        "id": f"evt_{kind}",
        "object": "event",
        "type": kind,
        "created": created,
        "data": {"object": obj},
    }


def deliver(service, evt: dict, secret: str = WEBHOOK_SECRET) -> str:
    payload = json.dumps(evt).encode()
    timestamp = int(time.time())
    digest = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return asyncio.run(service.handle_webhook(payload, f"t={timestamp},v1={digest}"))


def test_webhook_completes_the_payment():
    service, repo, _ = make(payment("pay-1", PaymentStatus.PENDING, provider_id="pi_1"))
    assert (
        deliver(service, event("payment_intent.succeeded", {"id": "pi_1"})) == "updated"
    )
    charge = {
        "id": "ch_1",
        "payment_intent": "pi_1",
        "receipt_url": "https://receipt",
        "payment_method_details": {"card": {"brand": "visa", "last4": "4242"}},
    }
    assert deliver(service, event("charge.succeeded", charge)) == "updated"
    paid = repo.items["pay-1"]
    assert (paid.status, paid.card_last4, paid.receipt_url) == (
        PaymentStatus.SUCCEEDED,
        "4242",
        "https://receipt",
    )
    assert paid.paid_at == datetime.datetime(
        2026, 11, 24, 10, 0, 42, tzinfo=datetime.UTC
    )


def test_webhook_failure_and_out_of_order_events():
    service, repo, _ = make(payment("pay-1", PaymentStatus.PENDING, provider_id="pi_1"))
    failed = {
        "id": "pi_1",
        "last_payment_error": {"message": "Your card was declined."},
    }
    deliver(service, event("payment_intent.payment_failed", failed))
    assert (repo.items["pay-1"].status, repo.items["pay-1"].failure_reason) == (
        PaymentStatus.FAILED,
        "Your card was declined.",
    )

    deliver(
        service, event("payment_intent.succeeded", {"id": "pi_1"})
    )  # paid on the second try
    assert repo.items["pay-1"].status is PaymentStatus.SUCCEEDED

    assert (
        deliver(service, event("payment_intent.payment_failed", failed))
        == "ignored: outdated event"
    )
    assert (
        repo.items["pay-1"].status is PaymentStatus.SUCCEEDED
    )  # a late failure does not undo a payment

    deliver(
        service, event("charge.refunded", {"payment_intent": "pi_1", "refunded": True})
    )
    assert repo.items["pay-1"].status is PaymentStatus.REFUNDED


def test_webhook_matches_by_metadata_and_ignores_the_rest():
    service, repo, _ = make(
        payment("pay-1", PaymentStatus.PENDING)
    )  # PaymentIntent ID not stored yet
    deliver(
        service,
        event(
            "payment_intent.succeeded",
            {"id": "pi_9", "metadata": {"payment_id": "pay-1"}},
        ),
    )
    assert (repo.items["pay-1"].status, repo.items["pay-1"].payment_provider_id) == (
        PaymentStatus.SUCCEEDED,
        "pi_9",
    )

    assert (
        deliver(service, event("payment_intent.succeeded", {"id": "pi_unknown"}))
        == "ignored: unknown payment"
    )
    assert (
        deliver(service, event("customer.created", {"id": "cus_1"}))
        == "ignored: customer.created"
    )


# --- routes -------------------------------------------------------------------------------------------------------


def client(uid: str, service: PaymentService):
    return fakes.client_as(uid, {get_payment_service: lambda: service})


def test_routes():
    service, _, _ = make()
    with client(fakes.BORROWER, service) as c:
        created = c.post(
            "/api/v1/payments",
            json={"loanApplicationId": "app-1", "feeType": "appraisal_processing"},
        )
        reused = c.post(
            "/api/v1/payments",
            json={"loanApplicationId": "app-1", "feeType": "appraisal_processing"},
        )
        history = c.get("/api/v1/payments").json()
        one = c.get("/api/v1/payments/pay-1")
        missing = c.get("/api/v1/payments/nope")

    assert created.status_code == 201 and reused.status_code == 200
    body = created.json()
    assert body["payment"]["status"] == "pending" and body["payment"]["amount"] == 149.0
    assert body["stripe"] == {
        "publishableKey": "pk_test_123",
        "paymentIntentClientSecret": "pi_pay-1_secret",
        "merchantDisplayName": "Agentic Lender",
    }
    assert "paymentProviderId" not in body["payment"]
    assert history["total"] == 1 and history["items"][0]["paymentId"] == "pay-1"
    assert one.status_code == 200 and missing.status_code == 404


def test_routes_reject_others_and_bad_signatures():
    service, _, _ = make()
    with client(fakes.BROKER, service) as c:
        assert (
            c.post(
                "/api/v1/payments",
                json={"loanApplicationId": "app-1", "feeType": "appraisal_processing"},
            ).status_code
            == 403
        )
        assert c.get("/api/v1/payments").status_code == 403
        assert c.post("/api/v1/payments", json={}).status_code in (403, 422)

    with client(fakes.BORROWER, service) as c:
        assert (
            c.post(
                "/api/v1/payments",
                json={"loanApplicationId": "app-1", "feeType": "free"},
            ).status_code
            == 422
        )
        bad = c.post(
            "/api/v1/payments/webhooks/stripe",
            content=b"{}",
            headers={"Stripe-Signature": "t=1,v1=bad"},
        )
        unsigned = c.post("/api/v1/payments/webhooks/stripe", content=b"{}")
    assert bad.status_code == 400 and unsigned.status_code == 400


def test_webhook_route_needs_no_login():
    service, repo, _ = make(payment("pay-1", PaymentStatus.PENDING, provider_id="pi_1"))
    payload = json.dumps(event("payment_intent.succeeded", {"id": "pi_1"})).encode()
    timestamp = int(time.time())
    digest = hmac.new(
        WEBHOOK_SECRET.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    with client(fakes.BORROWER, service) as c:
        from src.auth.dependencies import get_current_user
        from src.main import app

        app.dependency_overrides.pop(get_current_user)  # Stripe has no Firebase token
        response = c.post(
            "/api/v1/payments/webhooks/stripe",
            content=payload,
            headers={
                "Stripe-Signature": f"t={timestamp},v1={digest}",
                "Content-Type": "application/json",
            },
        )
    assert response.status_code == 200 and response.json() == {"received": True}
    assert repo.items["pay-1"].status is PaymentStatus.SUCCEEDED
