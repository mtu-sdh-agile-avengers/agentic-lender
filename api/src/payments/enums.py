from enum import StrEnum


class PaymentFeeType(StrEnum):
    """Fees a retail borrower can pay for a loan application (amounts in `payments.fees`)."""

    APPLICATION_VERIFICATION = (
        "application_verification"  # one-off check of income, debts and deposit
    )
    APPRAISAL_PROCESSING = (
        "appraisal_processing"  # fast-track: priority property appraisal (ALG4-103)
    )


class PaymentProvider(StrEnum):
    STRIPE = "stripe"  # the only provider (PayPal was dropped)


class PaymentStatus(StrEnum):
    """Lifecycle of a payment; only the Stripe webhook moves it past `pending`."""

    PENDING = (
        "pending"  # PaymentIntent created, the borrower has not paid (or is paying) yet
    )
    SUCCEEDED = "succeeded"  # money taken (test money in the sandbox)
    FAILED = (
        "failed"  # card declined, authentication failed or canceled; can be retried
    )
    REFUNDED = "refunded"  # refunded in full from the Stripe Dashboard
