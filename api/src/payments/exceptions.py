from fastapi import status

from src.exceptions import ApiError


class PaymentError(ApiError):
    """base exception class for payments"""


class PaymentNotFoundError(PaymentError):
    def __init__(self, payment_id: str) -> None:
        super().__init__(
            status.HTTP_404_NOT_FOUND, f"Payment (id: {payment_id}) is not found"
        )


class PaymentAlreadyPaidError(PaymentError):
    def __init__(self, loan_application_id: str, fee_type: str) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            f"The {fee_type} fee of loan application (id: {loan_application_id}) is already paid",
        )


class PaymentsNotConfiguredError(PaymentError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Payments are not configured: set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY (see docs/api/payments.md)",
        )


class PaymentProviderError(PaymentError):
    def __init__(self, detail: str) -> None:
        super().__init__(
            status.HTTP_502_BAD_GATEWAY, f"Stripe did not accept the request: {detail}"
        )


class PaymentWebhookSignatureError(PaymentError):
    def __init__(self) -> None:
        super().__init__(status.HTTP_400_BAD_REQUEST, "Invalid Stripe-Signature")


class PaymentApplicationClosedError(PaymentError):
    def __init__(self, loan_application_id: str) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            f"Loan application (id: {loan_application_id}) is closed; its fees can no longer be paid",
        )
