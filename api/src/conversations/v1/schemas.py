import datetime
from typing import Self

from pydantic import Field

from src.auth.enums import UserRole
from src.conversations.models import MAX_MESSAGE_LENGTH, ConversationModel, MessageModel
from src.conversations.service import InboxEntry
from src.schemas import BaseSchema


class ConversationCreateBody(BaseSchema):
    """Body of `POST /api/v1/conversations` (borrower only)."""

    loan_application_id: str
    with_officer: bool = Field(
        False,
        description="`true` to talk to the assigned bank officer; `false` (default) to talk to the broker",
    )


class MessageCreateBody(BaseSchema):
    """Body of `POST /api/v1/conversations/{id}/messages`."""

    text: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)


class OtherParticipant(BaseSchema):
    uid: str
    full_name: str | None = None
    role: UserRole | None = None


class ConversationResponse(BaseSchema):
    id: str
    loan_application_id: str
    interlocutor: OtherParticipant | None = None
    unread: bool = False
    last_message_preview: str | None = None
    last_sender_id: str | None = None
    last_message_at: datetime.datetime
    created_at: datetime.datetime

    @classmethod
    def from_conversation(cls, conversation: ConversationModel, user_uid: str) -> Self:
        return cls(
            id=conversation.id,
            loan_application_id=conversation.loan_application_id,
            unread=user_uid in conversation.unread_by,
            last_message_preview=conversation.last_message_preview,
            last_sender_id=conversation.last_sender_id,
            last_message_at=conversation.last_message_at,
            created_at=conversation.created_at,
        )

    @classmethod
    def from_inbox(cls, entry: InboxEntry, user_uid: str) -> Self:
        response = cls.from_conversation(entry.conversation, user_uid)
        if entry.other_participant is not None:
            response.interlocutor = OtherParticipant(
                uid=entry.other_participant.uid,
                full_name=entry.other_participant.full_name,
                role=entry.other_participant.role,
            )
        return response


class MessageResponse(BaseSchema):
    id: str
    sender_id: str
    sender_role: UserRole
    text: str
    created_at: datetime.datetime
    mine: bool

    @classmethod
    def from_message(cls, message: MessageModel, user_uid: str) -> Self:
        return cls(**message.model_dump(), mine=message.sender_id == user_uid)
