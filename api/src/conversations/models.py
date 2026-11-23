import datetime

from pydantic import BaseModel, Field

from src.auth.enums import UserRole
from src.utils import _get_utc_now

MAX_MESSAGE_LENGTH = 2000
PREVIEW_LENGTH = 120


class ConversationModel(BaseModel):
    id: str
    loan_application_id: str

    borrower_id: str
    staff_id: str
    participant_ids: list[str]  # [borrower_id, [staff_id]]; queried with array_contains
    unread_by: list[str] = Field(
        default_factory=list
    )  # participants with unseen messages

    last_message_preview: str | None = None
    last_sender_id: str | None = None
    last_message_at: datetime.datetime = Field(default_factory=_get_utc_now)

    created_at: datetime.datetime = Field(default_factory=_get_utc_now)


class MessageModel(BaseModel):
    id: str = ""
    sender_id: str
    sender_role: UserRole
    text: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)
    created_at: datetime.datetime = Field(default_factory=_get_utc_now)
