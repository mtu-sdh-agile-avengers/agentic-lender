from typing import Any

from src.enums import CollectionPath
from src.firebase.repository import FirestoreRepository
from src.support_tickets.models import SupportTicketModel


class SupportTicketFirestoreRepository(FirestoreRepository[SupportTicketModel]):
    col = CollectionPath.SUPPORT_TICKETS

    def _to_doc(self, entity: SupportTicketModel) -> dict[str, Any]:
        return entity.model_dump(exclude={"support_ticket_id"})

    def _from_doc(self, doc_id: str, data: dict[str, Any]) -> SupportTicketModel:
        return SupportTicketModel.model_validate({**data, "support_ticket_id": doc_id})

    def next_id(self) -> str:
        return (
            self._col_ref.document().id
        )  # generated locally by the SDK, no network call

    async def add_support_ticket(self, ticket: SupportTicketModel) -> None:
        await self._add(ticket.support_ticket_id, ticket)
