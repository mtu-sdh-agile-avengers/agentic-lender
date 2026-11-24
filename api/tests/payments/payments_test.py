"""ALG4-150 (contract and mocks) and ALG4-101 (Stripe sandbox)."""

import asyncio
import hashlib
import hmac
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
import stripe

from src.config import Config
from src.payments import fees
from src.payments.enums import PaymentFeeType, PaymentStatus
from src.payments.exceptions import (
    PaymentProviderError,
    PaymentsNotConfiguredError,
    PaymentWebhookSignatureError,
)
from src.payments.gateway import LiveStripeKeyError, StripeGateway, ensure_sandbox_keys
from src.payments.models import PaymentModel
from src.payments.v1.schemas import (
    PaymentCheckoutResponse,
    PaymentCreateBody,
    PaymentResponse,
)
from src.payments.webhooks import HANDLED_EVENTS, to_update
from src.schemas import PaginatedResponse

MOCKS = Path(__file__).resolve().parents[3] / "docs" / "api" / "mocks" / "payments"
WEBHOOK_SECRET = "whsec_test_secret"


def mock(name: str) -> dict:
    return json.loads((MOCKS / name).read_text(encoding="utf-8"))


# --- contract and mocks --------------------------------------------------------------------------


def test_fee_amounts_are_set_by_al_core():
    assert fees.amount_cents(PaymentFeeType.APPLICATION_VERIFICATION) == 4900
    assert fees.amount_euro(PaymentFeeType.APPRAISAL_PROCESSING) == 149.0
    assert set(fees.FEE_AMOUNTS_CENTS) == set(PaymentFeeType)


def test_mocks_follow_the_contract():
    body = PaymentCreateBody.model_validate(mock("create-payment.request.json"))
    assert body.fee_type is PaymentFeeType.APPRAISAL_PROCESSING

    checkout = PaymentCheckoutResponse.model_validate(
        mock("create-payment.response.json")
    )
    assert checkout.payment.status is PaymentStatus.PENDING
    assert checkout.stripe.publishable_key.startswith("pk_test_")
    assert checkout.payment.amount == fees.amount_euro(checkout.payment.fee_type)

    paid = PaymentResponse.model_validate(mock("payment-succeeded.response.json"))
    assert (paid.status, paid.card_last4) == (PaymentStatus.SUCCEEDED, "4242")
    failed = PaymentResponse.model_validate(mock("payment-failed.response.json"))
    assert failed.failure_reason == "Your card was declined."

    history = PaginatedResponse[PaymentResponse].model_validate(
        mock("payments-history.response.json")
    )
    assert [p.payment_id for p in history.items] == [
        "demo-payment-0001",
        "demo-payment-0002",
    ]


def test_mocks_are_exactly_what_the_api_serializes():
    for name in ("payment-succeeded.response.json", "payment-failed.response.json"):
        data = mock(name)
        dumped = PaymentResponse.model_validate(data).model_dump(
            mode="json", by_alias=True
        )
        assert dumped == data


def test_client_cannot_choose_the_amount_or_an_unknown_fee():
    body = PaymentCreateBody.model_validate(
        {"loanApplicationId": "a", "feeType": "application_verification", "amount": 1}
    )
    assert not hasattr(body, "amount")
    with pytest.raises(ValueError):
        PaymentCreateBody.model_validate(
            {"loanApplicationId": "a", "feeType": "free_money"}
        )


def test_provider_payment_id_stays_internal():
    payment = PaymentModel(
        payment_id="p1",
        user_id="u1",
        loan_application_id="a1",
        fee_type=PaymentFeeType.APPLICATION_VERIFICATION,
        amount=49.0,
        payment_provider_id="pi_123",
    )
    body = PaymentResponse.from_model(payment).model_dump(by_alias=True)
    assert "paymentProviderId" not in body and body["paymentId"] == "p1"


# --- webhook events ------------------------------------------------------------------------------------


def test_succeeded_and_charge_events_complete_the_payment():
    paid = to_update(mock("webhook.payment_intent.succeeded.json"))
    assert paid.payment_intent_id == "pi_3MockPaymentIntent0001"
    assert paid.fields["status"] is PaymentStatus.SUCCEEDED
    assert paid.fields["paid_at"].isoformat() == "2026-11-24T10:00:42+00:00"

    charge = to_update(mock("webhook.charge.succeeded.json"))
    assert charge.payment_intent_id == "pi_3MockPaymentIntent0001"
    assert charge.fields == {
        "receipt_url": "https://pay.stripe.com/receipts/payment/mock-receipt-0001",
        "card_brand": "visa",
        "card_last4": "4242",
    }


def test_failed_refunded_and_other_events():
    failed = to_update(mock("webhook.payment_intent.payment_failed.json"))
    assert failed.fields == {
        "status": PaymentStatus.FAILED,
        "failure_reason": "Your card was declined.",
    }

    refund = {
        "type": "charge.refunded",
        "data": {"object": {"payment_intent": "pi_1", "refunded": True}},
    }
    assert to_update(refund).fields == {"status": PaymentStatus.REFUNDED}
    partial = {
        "type": "charge.refunded",
        "data": {"object": {"payment_intent": "pi_1", "refunded": False}},
    }
    assert to_update(partial) is None
    assert (
        to_update({"type": "customer.created", "data": {"object": {"id": "cus_1"}}})
        is None
    )
    assert "payment_intent.succeeded" in HANDLED_EVENTS


# --- sandbox --------------------------------------------------------------------------------------------


def config(**values) -> Config:
    return Config(run_mode="dev", cors_origins=[], **values)


def test_live_keys_are_refused_outside_production():
    ensure_sandbox_keys(
        config(stripe_secret_key="sk_test_1", stripe_publishable_key="pk_test_1")
    )
    with pytest.raises(LiveStripeKeyError):
        ensure_sandbox_keys(config(stripe_secret_key="sk_live_1"))
    with pytest.raises(LiveStripeKeyError):
        ensure_sandbox_keys(config(stripe_publishable_key="pk_live_1"))
    ensure_sandbox_keys(
        Config(run_mode="prod", cors_origins=[], stripe_secret_key="sk_live_1")
    )


def signed(payload: bytes, secret: str = WEBHOOK_SECRET, at: int | None = None) -> str:
    timestamp = at or int(time.time())
    digest = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={digest}"


def test_webhook_signature_is_verified():
    gateway = StripeGateway("sk_test_1", "pk_test_1", WEBHOOK_SECRET)
    payload = json.dumps(mock("webhook.payment_intent.succeeded.json")).encode()

    event = gateway.parse_webhook(payload, signed(payload))
    assert event["type"] == "payment_intent.succeeded"
    assert to_update(event).fields["status"] is PaymentStatus.SUCCEEDED

    for signature in (
        None,
        "",
        signed(payload, secret="whsec_other"),
        signed(payload, at=int(time.time()) - 3600),
    ):
        with pytest.raises(PaymentWebhookSignatureError):
            gateway.parse_webhook(payload, signature)
    with pytest.raises(PaymentsNotConfiguredError):
        StripeGateway("sk_test_1", "pk_test_1", "").parse_webhook(
            payload, signed(payload)
        )


class FakePaymentIntents:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self.error = error

    async def create_async(self, params, options=None):
        self.calls.append({"params": params, "options": options})
        if self.error:
            raise self.error
        return {
            "id": "pi_1",
            "client_secret": "pi_1_secret_2",
            "status": "requires_payment_method",
            "amount": params["amount"],
            "currency": params["currency"],
        }


def gateway_with(intents: FakePaymentIntents) -> StripeGateway:
    return StripeGateway(
        "sk_test_1",
        "pk_test_1",
        client=SimpleNamespace(v1=SimpleNamespace(payment_intents=intents)),
    )


def create(gateway: StripeGateway):
    return asyncio.run(
        gateway.create_payment_intent(
            payment_id="pay-1",
            amount_cents=fees.amount_cents(PaymentFeeType.APPRAISAL_PROCESSING),
            currency=fees.CURRENCY,
            description="Fast-track appraisal",
            metadata={"loan_application_id": "app-1"},
        )
    )


def test_payment_intent_is_created_once_per_payment():
    intents = FakePaymentIntents()
    intent = create(gateway_with(intents))
    assert (intent.id, intent.client_secret, intent.amount) == (
        "pi_1",
        "pi_1_secret_2",
        14900,
    )
    call = intents.calls[0]
    assert call["options"] == {"idempotency_key": "payment-pay-1"}
    assert call["params"]["currency"] == "eur"
    assert call["params"]["metadata"] == {
        "loan_application_id": "app-1",
        "payment_id": "pay-1",
    }
    assert call["params"]["automatic_payment_methods"] == {"enabled": True}


def test_stripe_errors_and_missing_keys():
    with pytest.raises(PaymentProviderError):
        create(
            gateway_with(
                FakePaymentIntents(
                    stripe.InvalidRequestError("Amount too small", param="amount")
                )
            )
        )
    with pytest.raises(PaymentsNotConfiguredError):
        create(StripeGateway("", ""))
    assert not StripeGateway("", "").configured
    assert StripeGateway("sk_test_1", "pk_test_1").configured
