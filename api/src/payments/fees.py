"""Fee amounts. Set by AL-Core only: the client says which fee, never how much."""

from src.payments.enums import PaymentFeeType

CURRENCY = "eur"

# in cents, the unit Stripe uses (4900 = €49.00); the same amounts the mobile app shows
FEE_AMOUNTS_CENTS: dict[PaymentFeeType, int] = {
    PaymentFeeType.APPLICATION_VERIFICATION: 49_00,
    PaymentFeeType.APPRAISAL_PROCESSING: 149_00,
}

FEE_DESCRIPTIONS: dict[PaymentFeeType, str] = {
    PaymentFeeType.APPLICATION_VERIFICATION: "Application verification fee",
    PaymentFeeType.APPRAISAL_PROCESSING: "Fast-track appraisal",
}


def amount_cents(fee_type: PaymentFeeType) -> int:
    return FEE_AMOUNTS_CENTS[fee_type]


def amount_euro(fee_type: PaymentFeeType) -> float:
    return FEE_AMOUNTS_CENTS[fee_type] / 100
