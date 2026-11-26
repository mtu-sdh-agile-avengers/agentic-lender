"""Request and response bodies of the payments API (ALG4-150). Contract: docs/api/payments.md.

Endpoints (ALG4-227, ALG4-228, ALG4-232; `v1/router.py`):
    POST /api/v1/payments                   retail borrower starts paying a fee      -> PaymentCheckoutResponse
    GET  /api/v1/payments                   the borrower's payment history           -> PaginatedResponse[PaymentResponse]
    GET  /api/v1/payments/{payment_id}      one payment (the app polls it after paying) -> PaymentResponse
    POST /api/v1/payments/webhooks/stripe   Stripe -> AL-Core, signed, no bearer token -> WebhookAckResponse
"""

import datetime
from typing import Self

from pydantic import Field

from src.payments.enums import PaymentFeeType, PaymentProvider, PaymentStatus
from src.payments.models import PaymentModel
from src.payments.service import PaymentCheckout
from src.schemas import BaseSchema, PaginationQuery


class PaymentCreateBody(BaseSchema):
    """Body of `POST /api/v1/payments`. The amount is not sent: AL-Core sets it from the fee type."""

    loan_application_id: str = Field(min_length=1, max_length=128)
    fee_type: PaymentFeeType


class PaymentFilterQuery(PaginationQuery):
    """Query parameters of `GET /api/v1/payments` (+ `page`, `pageSize`)."""

    loan_application_id: str | None = Field(None, max_length=128)


class PaymentResponse(BaseSchema):
    payment_id: str
    loan_application_id: str
    fee_type: PaymentFeeType
    amount: float  # euro
    currency: str
    provider: PaymentProvider
    status: PaymentStatus
    receipt_url: str | None
    failure_reason: str | None
    card_brand: str | None
    card_last4: str | None
    created_at: datetime.datetime
    paid_at: datetime.datetime | None

    @classmethod
    def from_model(cls, model: PaymentModel) -> Self:
        # `payment_provider_id` (the Stripe PaymentIntent ID) stays internal
        return cls.model_validate(model.model_dump(exclude={"payment_provider_id"}))


class StripePaymentSheetResponse(BaseSchema):
    """What the Android app needs to open Stripe's PaymentSheet; never contains the secret key."""

    # pk_test_... in the sandbox; PaymentConfiguration.init(context, publishableKey)
    publishable_key: str
    # paymentSheet.presentWithPaymentIntent(paymentIntentClientSecret, configuration)
    payment_intent_client_secret: str
    # PaymentSheet.Configuration(merchantDisplayName)
    merchant_display_name: str


class PaymentCheckoutResponse(BaseSchema):
    """Response of `POST /api/v1/payments`: the (pending) payment and how to pay it."""

    payment: PaymentResponse
    stripe: StripePaymentSheetResponse

    @classmethod
    def from_checkout(
        cls, checkout: PaymentCheckout, merchant_display_name: str
    ) -> Self:
        return cls(
            payment=PaymentResponse.from_model(checkout.payment),
            stripe=StripePaymentSheetResponse(
                publishable_key=checkout.publishable_key,
                payment_intent_client_secret=checkout.intent.client_secret,
                merchant_display_name=merchant_display_name,
            ),
        )


class WebhookAckResponse(BaseSchema):
    received: bool = True
