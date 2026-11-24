"""Payments of retail borrowers through Stripe (ALG4-227 start, ALG4-228 webhook, ALG4-232 history).

Contract: docs/api/payments.md. Only the webhook moves a payment past `pending`: the app's word that it paid is never
trusted, Stripe's signed event is.
"""

from dataclasses import dataclass

from loguru import logger

from src.auth.models import CurrentUserModel
from src.loan_applications.enums import LoanApplicationStatus
from src.loan_applications.exceptions import LoanApplicationNotFoundError
from src.loan_applications.ports import LoanApplicationRepositoryPort
from src.payments import fees
from src.payments.enums import PaymentFeeType, PaymentStatus
from src.payments.exceptions import (
    PaymentAlreadyPaidError,
    PaymentApplicationClosedError,
    PaymentNotFoundError,
    PaymentsNotConfiguredError,
)
from src.payments.gateway import StripeIntent
from src.payments.models import PaymentModel
from src.payments.ports import PaymentGatewayPort, PaymentRepositoryPort
from src.payments.webhooks import to_update
from src.schemas import PaginatedResponse

# Stripe PaymentIntent statuses in which the same intent can still be paid (e.g. after a declined card)
REUSABLE_INTENT_STATUSES = frozenset(
    {
        "requires_payment_method",
        "requires_confirmation",
        "requires_action",
        "processing",
    }
)

# which status a webhook may move a payment to; late or repeated events must not undo a result
# (e.g. a delayed "payment_failed" arriving after "succeeded", or anything after a refund)
ALLOWED_STATUS_CHANGES: dict[PaymentStatus, frozenset[PaymentStatus]] = {
    PaymentStatus.PENDING: frozenset(PaymentStatus),
    PaymentStatus.FAILED: frozenset(
        {PaymentStatus.PENDING, PaymentStatus.FAILED, PaymentStatus.SUCCEEDED}
    ),
    PaymentStatus.SUCCEEDED: frozenset(
        {PaymentStatus.SUCCEEDED, PaymentStatus.REFUNDED}
    ),
    PaymentStatus.REFUNDED: frozenset({PaymentStatus.REFUNDED}),
}


@dataclass(frozen=True)
class PaymentCheckout:
    """A payment the borrower is about to pay, with what the app needs to open Stripe's payment sheet."""

    payment: PaymentModel
    intent: StripeIntent
    publishable_key: str
    created: bool  # False if an unpaid payment of the same fee was reused


class PaymentService:
    def __init__(
        self,
        payments: PaymentRepositoryPort,
        applications: LoanApplicationRepositoryPort,
        gateway: PaymentGatewayPort,
    ) -> None:
        self._payments = payments
        self._applications = applications
        self._gateway = gateway

    # --- ALG4-227: start paying a fee -------------------------------------------------------------------------

    async def start(
        self,
        current_user: CurrentUserModel,
        *,
        loan_application_id: str,
        fee_type: PaymentFeeType,
    ) -> PaymentCheckout:
        """Starts paying a fee of one of the borrower's applications, or continues an unpaid one.

        The amount comes from `payments.fees`, never from the client. If this fee already has an unpaid
        (`pending` or `failed`) payment, that payment and its PaymentIntent are reused, so retrying never charges
        twice; a new one is created otherwise.

        Raises:
            PaymentsNotConfiguredError: if Stripe keys are not set (503).
            LoanApplicationNotFoundError: if the application does not exist or is not the borrower's (404).
            PaymentApplicationClosedError: if the application is closed (409).
            PaymentAlreadyPaidError: if this fee is already paid (409).
            PaymentProviderError: if Stripe rejects the request (502).
        """
        if not self._gateway.configured:
            raise PaymentsNotConfiguredError

        application = await self._applications.get_loan_application(loan_application_id)
        if application is None or application.borrower_id != current_user.uid:
            raise LoanApplicationNotFoundError(loan_application_id)
        if application.status == LoanApplicationStatus.CLOSED:
            raise PaymentApplicationClosedError(loan_application_id)

        same_fee = [
            p
            for p in await self._payments.get_user_payments(current_user.uid)
            if p.loan_application_id == loan_application_id and p.fee_type == fee_type
        ]
        if any(p.status == PaymentStatus.SUCCEEDED for p in same_fee):
            raise PaymentAlreadyPaidError(loan_application_id, fee_type)

        unpaid = sorted(
            (
                p
                for p in same_fee
                if p.status in (PaymentStatus.PENDING, PaymentStatus.FAILED)
            ),
            key=lambda p: p.created_at,
            reverse=True,
        )
        if unpaid:
            checkout = await self._resume(unpaid[0])
            if checkout is not None:
                return checkout

        payment = PaymentModel(
            payment_id=self._payments.next_id(),
            user_id=current_user.uid,
            loan_application_id=loan_application_id,
            fee_type=fee_type,
            amount=fees.amount_euro(fee_type),
        )
        # saved before Stripe is asked: if Stripe fails, the next request resumes this payment (same idempotency key)
        await self._payments.add_payment(payment)
        intent = await self._create_intent(payment)
        return self._checkout(payment, intent, created=True)

    async def _resume(self, payment: PaymentModel) -> PaymentCheckout | None:
        """Continues an unpaid payment; `None` if its PaymentIntent can no longer be paid (then a new one is made).

        Raises:
            PaymentAlreadyPaidError: if Stripe says it was paid after all (the webhook was missed); the payment is
                marked as succeeded first.
        """
        if payment.payment_provider_id is None:  # Stripe failed last time: try again
            intent = await self._create_intent(payment)
            return self._checkout(payment, intent, created=False)

        intent = await self._gateway.retrieve_payment_intent(
            payment.payment_provider_id
        )
        if intent.status == "succeeded":
            await self._payments.update_payment(
                payment.payment_id, {"status": PaymentStatus.SUCCEEDED}
            )
            raise PaymentAlreadyPaidError(payment.loan_application_id, payment.fee_type)
        if intent.status not in REUSABLE_INTENT_STATUSES:  # canceled
            return None

        if payment.status != PaymentStatus.PENDING:
            fields = {"status": PaymentStatus.PENDING, "failure_reason": None}
            await self._payments.update_payment(payment.payment_id, fields)
            payment = payment.model_copy(update=fields)
        return self._checkout(payment, intent, created=False)

    async def _create_intent(self, payment: PaymentModel) -> StripeIntent:
        intent = await self._gateway.create_payment_intent(
            payment_id=payment.payment_id,
            amount_cents=fees.amount_cents(payment.fee_type),
            currency=fees.CURRENCY,
            description=fees.FEE_DESCRIPTIONS[payment.fee_type],
            metadata={
                "loan_application_id": payment.loan_application_id,
                "fee_type": str(payment.fee_type),
                "user_id": payment.user_id,
            },
        )
        await self._payments.update_payment(
            payment.payment_id, {"payment_provider_id": intent.id}
        )
        return intent

    def _checkout(
        self, payment: PaymentModel, intent: StripeIntent, *, created: bool
    ) -> PaymentCheckout:
        return PaymentCheckout(
            payment=payment.model_copy(update={"payment_provider_id": intent.id}),
            intent=intent,
            publishable_key=self._gateway.publishable_key,
            created=created,
        )

    # --- ALG4-232: history ---------------------------------------------------------------------------------------

    async def get_history(
        self,
        current_user: CurrentUserModel,
        *,
        loan_application_id: str | None = None,
        page: int = 1,
        page_size: int = 15,
    ) -> PaginatedResponse[PaymentModel]:
        """The borrower's payments, newest first; optionally of one application."""
        payments = [
            p
            for p in await self._payments.get_user_payments(current_user.uid)
            if loan_application_id is None
            or p.loan_application_id == loan_application_id
        ]
        payments.sort(key=lambda p: p.created_at, reverse=True)
        start = (page - 1) * page_size
        return PaginatedResponse.build(
            items=payments[start : start + page_size],
            page=page,
            page_size=page_size,
            total=len(payments),
        )

    async def get(
        self, current_user: CurrentUserModel, payment_id: str
    ) -> PaymentModel:
        """One of the borrower's payments; the app polls it after the payment sheet closes.

        Raises:
            PaymentNotFoundError: if it does not exist or belongs to someone else (404).
        """
        payment = await self._payments.get_payment(payment_id)
        if payment is None or payment.user_id != current_user.uid:
            raise PaymentNotFoundError(payment_id)
        return payment

    # --- ALG4-228: webhook ----------------------------------------------------------------------------------------

    async def handle_webhook(self, payload: bytes, signature: str | None) -> str:
        """Applies one signed Stripe event to its payment.

        Events that do not concern a payment, or concern an unknown one, are acknowledged and ignored, so Stripe does
        not retry them. Repeated or late events are harmless (see `ALLOWED_STATUS_CHANGES`).

        Returns:
            str: what happened, for the log (`updated`, `ignored: ...`).

        Raises:
            PaymentsNotConfiguredError: if STRIPE_WEBHOOK_SECRET is not set (503).
            PaymentWebhookSignatureError: if the signature is missing or wrong (400).
        """
        event = self._gateway.parse_webhook(payload, signature)
        update = to_update(event)
        if update is None:
            return f"ignored: {event.get('type')}"

        payment = await self._payments.find_by_provider_id(update.payment_intent_id)
        if payment is None and update.payment_id:
            candidate = await self._payments.get_payment(update.payment_id)
            if candidate is not None and candidate.payment_provider_id in (
                None,
                update.payment_intent_id,
            ):
                payment = candidate
        if payment is None:
            logger.warning(
                f"Stripe event {event.get('id')} ({event.get('type')}) for unknown PaymentIntent {update.payment_intent_id}"
            )
            return "ignored: unknown payment"

        fields = dict(update.fields)
        new_status = fields.get("status")
        if (
            new_status is not None
            and new_status not in ALLOWED_STATUS_CHANGES[payment.status]
        ):
            fields = {
                k: v
                for k, v in fields.items()
                if k not in ("status", "failure_reason", "paid_at")
            }
        if payment.payment_provider_id is None:
            fields["payment_provider_id"] = update.payment_intent_id
        if not fields:
            return "ignored: outdated event"

        await self._payments.update_payment(payment.payment_id, fields)
        logger.info(
            f"payment {payment.payment_id}: {event.get('type')} -> {sorted(fields)}"
        )
        return "updated"
