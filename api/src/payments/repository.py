from typing import Any

from google.cloud.firestore import FieldFilter

from src.enums import CollectionPath
from src.firebase.repository import FirestoreRepository
from src.payments.models import PaymentModel

# a borrower has a handful of payments (two fee types per application); read at most this many
MAX_USER_PAYMENTS = 500


class PaymentFirestoreRepository(FirestoreRepository[PaymentModel]):
    col = CollectionPath.PAYMENTS

    def _to_doc(self, entity: PaymentModel) -> dict[str, Any]:
        return entity.model_dump(exclude={"payment_id"})

    def _from_doc(self, doc_id: str, data: dict[str, Any]) -> PaymentModel:
        return PaymentModel.model_validate({**data, "payment_id": doc_id})

    def next_id(self) -> str:
        return (
            self._col_ref.document().id
        )  # generated locally by the SDK, no network call

    async def add_payment(self, payment: PaymentModel) -> None:
        await self._add(payment.payment_id, payment)

    async def get_payment(self, payment_id: str) -> PaymentModel | None:
        return await self._get(payment_id)

    async def update_payment(self, payment_id: str, fields: dict[str, Any]) -> None:
        await self._update(payment_id, fields)

    async def get_user_payments(self, user_id: str) -> list[PaymentModel]:
        """Every payment of one borrower, in no particular order.

        One equality filter only, so no composite index is needed; the service filters, sorts and pages them.
        """
        query = self._col_ref.where(filter=FieldFilter("user_id", "==", user_id))
        return await self._stream(query.limit(MAX_USER_PAYMENTS))

    async def find_by_provider_id(
        self, payment_provider_id: str
    ) -> PaymentModel | None:
        """The payment of a Stripe PaymentIntent (`pi_...`), used to match webhook events."""
        query = self._col_ref.where(
            filter=FieldFilter("payment_provider_id", "==", payment_provider_id)
        )
        found = await self._stream(query.limit(1))
        return found[0] if found else None
