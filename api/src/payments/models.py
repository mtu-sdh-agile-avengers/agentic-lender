import datetime

from pydantic import BaseModel, Field

from src.payments.enums import PaymentFeeType, PaymentProvider, PaymentStatus
from src.payments.fees import CURRENCY
from src.utils import _get_utc_now


class PaymentModel(BaseModel):
    """A fee paid by a retail borrower for a loan application (`payments/{payment_id}`).

    Created by AL-Core when the borrower starts paying; after that only the Stripe webhook changes it.
    Card details never reach AL-Core or Firestore: the card is entered in Stripe's own payment sheet.
    """

    payment_id: str  # document name, not a field
    user_id: str  # borrower who pays
    loan_application_id: str
    fee_type: PaymentFeeType
    amount: float  # in euro, from `payments.fees`
    currency: str = CURRENCY
    provider: PaymentProvider = PaymentProvider.STRIPE
    payment_provider_id: str | None = (
        None  # Stripe PaymentIntent ID (pi_...); matches webhook events to the payment
    )
    status: PaymentStatus = PaymentStatus.PENDING
    receipt_url: str | None = None  # Stripe receipt; evidence of payment
    failure_reason: str | None = None
    card_brand: str | None = None  # e.g. visa; shown in the payment history
    card_last4: str | None = None
    created_at: datetime.datetime = Field(default_factory=_get_utc_now)
    paid_at: datetime.datetime | None = None
