from src.auth.models import CurrentUserModel
from src.loan_applications.ports import LoanApplicationRepositoryPort
from src.support_tickets.enums import SupportTicketCategory
from src.support_tickets.exceptions import SupportTicketLoanApplicationError
from src.support_tickets.models import SupportTicketModel
from src.support_tickets.ports import SupportTicketRepositoryPort


class SupportTicketService:
    def __init__(
        self,
        tickets: SupportTicketRepositoryPort,
        applications: LoanApplicationRepositoryPort,
    ) -> None:
        self._tickets = tickets
        self._applications = applications

    async def submit(
        self,
        current_user: CurrentUserModel,
        *,
        category: SupportTicketCategory,
        description: str,
        loan_application_id: str | None = None,
    ) -> SupportTicketModel:
        """Saves a support request of a retail borrower (ALG4-218).

        Args:
            current_user: retail borrower who sent the request.
            category: what the issue is about.
            description: the issue in the borrower's words (already trimmed and validated by the schema).
            loan_application_id: the application the issue is about; only for the `loan_application` category.

        Returns:
            SupportTicketModel: the saved ticket, `open`.

        Raises:
            SupportTicketLoanApplicationError: if the application does not exist or is not the borrower's own.
        """
        if category == SupportTicketCategory.LOAN_APPLICATION and loan_application_id:
            application = await self._applications.get_loan_application(
                loan_application_id
            )
            # "does not exist" and "not yours" give the same answer
            if application is None or application.borrower_id != current_user.uid:
                raise SupportTicketLoanApplicationError(loan_application_id)

        ticket = SupportTicketModel(
            support_ticket_id=self._tickets.next_id(),
            user_id=current_user.uid,
            category=category,
            description=description,
            loan_application_id=loan_application_id,
        )
        await self._tickets.add_support_ticket(ticket)
        return ticket
