from enum import StrEnum


class SupportTicketCategory(StrEnum):
    ACCOUNT = "account"
    LOAN_APPLICATION = (
        "loan_application"  # the only category tied to a loan application
    )
    PAYMENT = "payment"
    TECHNICAL = "technical"
    OTHER = "other"


class SupportTicketStatus(StrEnum):
    OPEN = "open"  # on submission
    RESOLVED = "resolved"  # closed by the support team (outside AL-Core for now)
