import datetime

from pydantic import BaseModel, Field

from src.support_tickets.enums import SupportTicketCategory, SupportTicketStatus
from src.utils import _get_utc_now

MAX_DESCRIPTION_LENGTH = 1000


class SupportTicketModel(BaseModel):
    """Support request of a retail borrower (`support_tickets/{support_ticket_id}`); read-only once created."""

    support_ticket_id: str  # document name, not a field
    user_id: str
    category: SupportTicketCategory
    description: str = Field(min_length=1, max_length=MAX_DESCRIPTION_LENGTH)
    loan_application_id: str | None = None  # only for `loan_application` tickets
    status: SupportTicketStatus = SupportTicketStatus.OPEN
    created_at: datetime.datetime = Field(default_factory=_get_utc_now)
    resolved_at: datetime.datetime | None = None
