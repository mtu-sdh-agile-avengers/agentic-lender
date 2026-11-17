from fastapi import status

from src.exceptions import ApiError
from src.auth.enums import UserRole
from src.loan_applications.enums import LoanApplicationStatus


class LoanApplicationError(ApiError):
    """base exception class for loan application errors (firestore)"""


class LoanApplicationIsNotOpenError(LoanApplicationError):
    def __init__(
        self, loan_application_id: str, current: LoanApplicationStatus
    ) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            f"Loan application (uid: {loan_application_id}) assignees cannot be changed: its status is {current}",
        )


class LoanApplicationAccessError(LoanApplicationError):
    def __init__(self, loan_application_id: str) -> None:
        super().__init__(
            status.HTTP_403_FORBIDDEN,
            f"You are not assigned to loan application (id: {loan_application_id})",
        )


class LoanApplicationInvalidAssigneeError(LoanApplicationError):
    def __init__(self, uid: str, role: UserRole) -> None:
        super().__init__(
            status.HTTP_403_FORBIDDEN,
            f"User (uid: {uid}) does not exist or is not {role})",
        )


class LoanApplicationAssigneeAlreadySetError(LoanApplicationError):
    def __init__(self, loan_application_id: str, role_label: str) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            f"Loan application (id: {loan_application_id}) already has a {role_label} assigned",
        )


class LoanApplicationBrokerIsNotAssignedError(LoanApplicationError):
    def __init__(self, loan_application_id: str) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            f"Loan application (id: {loan_application_id}) needs to be claimed by broker before"
            f"any further actions",
        )


class LoanApplicationStatusChangeError(LoanApplicationError):
    def __init__(
        self, current: LoanApplicationStatus, requested: LoanApplicationStatus
    ) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            f"Loan application status cannot be changed from {current} to {requested}",
        )


class LoanApplicationNotFoundError(LoanApplicationError):
    def __init__(self, loan_application_id: str) -> None:
        super().__init__(
            status.HTTP_404_NOT_FOUND,
            f"Loan application (id: {loan_application_id}) is not found",
        )
