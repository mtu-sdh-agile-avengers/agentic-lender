from fastapi import status

from src.exceptions import ApiError


class AuditPackError(ApiError):
    """base exception class for audit packs"""


class AuditPackNotAvailableError(AuditPackError):
    def __init__(self, loan_application_id: str) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            f"Loan application (id: {loan_application_id}) has no lending decision yet; "
            "an audit pack is available once it is approved or declined",
        )
