from enum import StrEnum


class AssessmentStatus(StrEnum):
    """State of an AI committee run; mirrors the AL-AI Engine job status."""

    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class AIDecision(StrEnum):
    APPROVE = "Approve"
    CONDITIONALLY_APPROVE = "Conditionally Approve"
    DECLINE = "Decline"
    UNAVAILABLE = "Unavailable"  # no LLM provider returned a usable answer
    ERROR = "Error"  # a provider answered, but not with valid JSON
