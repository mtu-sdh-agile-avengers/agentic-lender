from fastapi import APIRouter, Request, status

from src.auth.dependencies import BorrowerDep
from src.rate_limiting import limiter
from src.support_tickets.dependencies import SupportTicketServiceDep
from src.support_tickets.v1.schemas import (
    SupportTicketCreateBody,
    SupportTicketResponse,
)

router = APIRouter(prefix="/api/v1/support-tickets", tags=["support-tickets"])


# POST /api/v1/support-tickets
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    description=(
        "Submits a support request (retail borrower). `loanApplicationId` is required for the "
        "`loan_application` category and must be one of the borrower's own applications."
    ),
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Loan application not found among the borrower's"
        },
    },
)
@limiter.limit("5/minute")
async def submit_support_ticket(
    request: Request,
    data: SupportTicketCreateBody,
    current_user: BorrowerDep,
    service: SupportTicketServiceDep,
) -> SupportTicketResponse:
    ticket = await service.submit(
        current_user,
        category=data.category,
        description=data.description,
        loan_application_id=data.loan_application_id,
    )
    return SupportTicketResponse.from_model(ticket)
