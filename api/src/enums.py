from enum import StrEnum


class CollectionPath(StrEnum):
    USERS = "users"
    VALUATIONS = "valuations"

    LOAN_APPLICATIONS = "loan_applications"
    DOCUMENTS = "documents"
    ASSESSMENTS = "assessments"

    SUPPORT_TICKETS = "support_tickets"
    REVIEWS = "reviews"

    CONVERSATIONS = "conversations"
    MESSAGES = "messages"

    STRESS_TESTS = "stress_tests"
    PAYMENTS = "payments"
