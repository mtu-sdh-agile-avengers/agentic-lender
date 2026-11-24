from fastapi import status

from src.exceptions import ApiError


class SupportTicketError(ApiError):
    """base exception class for support tickets"""


class SupportTicketLoanApplicationError(SupportTicketError):
    def __init__(self, loan_application_id: str) -> None:
        super().__init__(
            status.HTTP_404_NOT_FOUND,
            f"Loan application (id: {loan_application_id}) is not found among your applications",
        )
