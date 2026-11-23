from typing import Annotated

from fastapi import Depends

from src.firebase.dependencies import FirestoreDep
from src.loan_applications.repository import LoanApplicationFirestoreRepository
from src.support_tickets.repository import SupportTicketFirestoreRepository
from src.support_tickets.service import SupportTicketService


def get_support_ticket_service(db: FirestoreDep) -> SupportTicketService:
    return SupportTicketService(
        SupportTicketFirestoreRepository(db),
        LoanApplicationFirestoreRepository(db),
    )


SupportTicketServiceDep = Annotated[
    SupportTicketService, Depends(get_support_ticket_service)
]
