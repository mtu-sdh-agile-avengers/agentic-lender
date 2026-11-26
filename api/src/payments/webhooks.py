"""What a Stripe webhook event means for a payment (pure functions, no I/O).

Stripe sends events about its own objects; `to_update` turns the ones AL-Core cares about into the fields to change
on the matching payment (matched by `payment_provider_id`, the PaymentIntent ID). Configure the webhook endpoint
(Dashboard or `stripe listen --events ...`) with exactly `HANDLED_EVENTS`.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any

from src.payments.enums import PaymentStatus

HANDLED_EVENTS = (
    "payment_intent.succeeded",  # paid -> succeeded
    "payment_intent.payment_failed",  # declined / authentication failed -> failed (can be retried)
    "payment_intent.canceled",  # -> failed
    "charge.succeeded",  # receipt link and card brand / last 4 digits
    "charge.refunded",  # refunded in full -> refunded
)


@dataclass(frozen=True)
class PaymentUpdate:
    """Fields to set on the payment whose `payment_provider_id` is `payment_intent_id`.

    `payment_id` comes from the PaymentIntent's metadata (PaymentIntent events only): a fallback match in case the
    payment does not have its PaymentIntent ID stored yet.
    """

    payment_intent_id: str
    fields: dict[str, Any] = field(default_factory=dict)
    payment_id: str | None = None


def _time(timestamp: int | None) -> datetime.datetime | None:
    return (
        datetime.datetime.fromtimestamp(timestamp, datetime.UTC) if timestamp else None
    )


def to_update(event: dict[str, Any]) -> PaymentUpdate | None:
    """Translates one webhook event; `None` for events that do not change a payment.

    Args:
        event: verified event from `StripeGateway.parse_webhook`.

    Returns:
        PaymentUpdate | None: the payment to change and how.
    """
    kind = event.get("type")
    obj: dict[str, Any] = (event.get("data") or {}).get("object") or {}
    payment_id = (obj.get("metadata") or {}).get("payment_id")

    match kind:
        case "payment_intent.succeeded":
            return PaymentUpdate(
                obj["id"],
                {
                    "status": PaymentStatus.SUCCEEDED,
                    "failure_reason": None,
                    "paid_at": _time(event.get("created")),
                },
                payment_id,
            )
        case "payment_intent.payment_failed":
            error = obj.get("last_payment_error") or {}
            return PaymentUpdate(
                obj["id"],
                {
                    "status": PaymentStatus.FAILED,
                    "failure_reason": error.get("message") or "The payment failed",
                },
                payment_id,
            )
        case "payment_intent.canceled":
            return PaymentUpdate(
                obj["id"],
                {
                    "status": PaymentStatus.FAILED,
                    "failure_reason": obj.get("cancellation_reason") or "canceled",
                },
                payment_id,
            )
        case "charge.succeeded" if obj.get("payment_intent"):
            card = (obj.get("payment_method_details") or {}).get("card") or {}
            return PaymentUpdate(
                obj["payment_intent"],
                {
                    "receipt_url": obj.get("receipt_url"),
                    "card_brand": card.get("brand"),
                    "card_last4": card.get("last4"),
                },
            )
        case "charge.refunded" if obj.get("payment_intent") and obj.get("refunded"):
            return PaymentUpdate(
                obj["payment_intent"], {"status": PaymentStatus.REFUNDED}
            )
    return None
