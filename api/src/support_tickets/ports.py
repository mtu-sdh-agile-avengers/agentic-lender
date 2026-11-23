from typing import Protocol

from src.support_tickets.models import SupportTicketModel


class SupportTicketRepositoryPort(Protocol):
    def next_id(self) -> str: ...
    async def add_support_ticket(self, ticket: SupportTicketModel) -> None: ...
