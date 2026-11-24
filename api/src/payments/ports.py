from typing import Any, Protocol

from src.payments.gateway import StripeIntent
from src.payments.models import PaymentModel


class PaymentRepositoryPort(Protocol):
    def next_id(self) -> str: ...
    async def add_payment(self, payment: PaymentModel) -> None: ...
    async def get_payment(self, payment_id: str) -> PaymentModel | None: ...
    async def update_payment(self, payment_id: str, fields: dict[str, Any]) -> None: ...
    async def get_user_payments(self, user_id: str) -> list[PaymentModel]: ...
    async def find_by_provider_id(
        self, payment_provider_id: str
    ) -> PaymentModel | None: ...


# the part of StripeGateway the payment service needs (tests pass a fake)
class PaymentGatewayPort(Protocol):
    publishable_key: str

    @property
    def configured(self) -> bool: ...
    async def create_payment_intent(
        self,
        *,
        payment_id: str,
        amount_cents: int,
        currency: str,
        description: str,
        metadata: dict[str, str],
    ) -> StripeIntent: ...
    async def retrieve_payment_intent(self, payment_intent_id: str) -> StripeIntent: ...
    def parse_webhook(
        self, payload: bytes, signature: str | None
    ) -> dict[str, Any]: ...
