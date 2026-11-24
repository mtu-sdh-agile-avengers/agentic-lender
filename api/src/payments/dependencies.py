from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.config import get_config
from src.payments.gateway import StripeGateway


@lru_cache  # one Stripe client (and connection pool) for the whole app
def get_stripe_gateway() -> StripeGateway:
    """The Stripe sandbox; `configured` is False (payments answer 503) until the keys are set."""
    return StripeGateway.from_config(get_config())


StripeGatewayDep = Annotated[StripeGateway, Depends(get_stripe_gateway)]
