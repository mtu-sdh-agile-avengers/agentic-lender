from fastapi import status

from src.exceptions import ApiError


class AssessmentError(ApiError):
    """base exception class for AI committee assessments"""


class AssessmentNotFoundError(AssessmentError):
    def __init__(self, loan_application_id: str) -> None:
        super().__init__(
            status.HTTP_404_NOT_FOUND,
            f"Loan application (id: {loan_application_id}) has not been assessed by the AI committee yet",
        )
