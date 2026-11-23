from src.auth.enums import UserRole
from src.auth.models import CurrentUserModel
from src.loan_applications.models import LoanApplicationModel

# allows to check which field of an LoanApplicationModel holds uid of the caller.
ASSIGNEE_FIELD: dict[UserRole, str] = {
    UserRole.BORROWER: "borrower_id",
    UserRole.BROKER: "broker_id",
    UserRole.BANK_OFFICER: "bank_officer_id",
}


def _is_assignee(
    current_user: CurrentUserModel, application: LoanApplicationModel
) -> bool:
    """Checks if the current user is assigned to the loan application.

    Args:
        current_user: user who sent request.
        application: loan application to check.

    Returns:
        bool: `True` if the application's field for the user's role holds uid of the current user, i.e.
        current user is assigned to this application for a certain role (`borrower`, `broker`, or `bank_officer`);
        `False` otherwise.
    """
    if current_user.role is None:
        return False

    field = ASSIGNEE_FIELD.get(current_user.role)
    return field is not None and getattr(application, field) == current_user.uid


def has_view_access(
    current_user: CurrentUserModel, application: LoanApplicationModel
) -> bool:
    """Checks if the current user has the view (i.e., READ) access to the loan application.

    Args:
        current_user: user who sent request.
        application: loan application to check.

    Returns:
        bool: `True` if the current user may see the application; `False` otherwise.
    """
    if current_user.role == UserRole.BROKER and application.broker_id is None:
        return True
    return _is_assignee(current_user, application)


def has_modify_access(
    current_user: CurrentUserModel, application: LoanApplicationModel
) -> bool:
    """Checks if the current user has the modify (i.e., WRITE) access to the loan application.

    Args:
        current_user: user who sent request.
        application: loan application to check.

    Returns:
        bool: `True` if the current user may modify the application details; otherwise `False`.
    """
    return _is_assignee(current_user, application)
