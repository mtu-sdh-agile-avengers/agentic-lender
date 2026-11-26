from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.config import get_config
from src.firebase.dependencies import FirestoreDep
from src.loan_applications.repository import LoanApplicationFirestoreRepository
from src.payments.gateway import StripeGateway
from src.payments.repository import PaymentFirestoreRepository
from src.payments.service import PaymentService


@lru_cache  # one Stripe client (and connection pool) for the whole app
def get_stripe_gateway() -> StripeGateway:
    """The Stripe sandbox; `configured` is False (payments answer 503) until the keys are set."""
    return StripeGateway.from_config(get_config())


StripeGatewayDep = Annotated[StripeGateway, Depends(get_stripe_gateway)]


def get_payment_service(db: FirestoreDep, gateway: StripeGatewayDep) -> PaymentService:
    return PaymentService(
        PaymentFirestoreRepository(db),
        LoanApplicationFirestoreRepository(db),
        gateway,
    )


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]
