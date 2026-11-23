import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from src.auth.dependencies import CurrentUserDep, require_roles
from src.auth.enums import UserRole
from src.auth.models import CurrentUserModel
from src.conversations.dependencies import ConversationServiceDep
from src.conversations.v1.schemas import (
    ConversationCreateBody,
    ConversationResponse,
    MessageCreateBody,
    MessageResponse,
)
from src.rate_limiting import limiter

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])

BorrowerDep = Annotated[CurrentUserModel, Depends(require_roles(UserRole.BORROWER))]
ParticipantDep = Annotated[
    CurrentUserModel,
    Depends(require_roles(UserRole.BORROWER, UserRole.BROKER, UserRole.BANK_OFFICER)),
]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    description=(
        "Borrower opens the conversation about one of their applications with the broker (or, without a "
        "broker, the assigned bank officer). Idempotent: an existing conversation is returned."
    ),
    responses={
        404: {"detail": "Loan application not found"},
        409: {"detail": "No broker or officer assigned"},
    },
)
@limiter.limit("10/minute")
async def open_conversation(
    request: Request,
    data: ConversationCreateBody,
    current_user: BorrowerDep,
    service: ConversationServiceDep,
) -> ConversationResponse:
    conversation = await service.open_conversation(
        current_user, data.loan_application_id
    )
    return ConversationResponse.from_conversation(conversation, current_user.uid)


@router.get(
    "",
    description="Inbox of the current user: conversations they take part in, most recent activity first.",
)
@limiter.limit("60/minute")
async def list_conversations(
    request: Request,
    current_user: ParticipantDep,
    service: ConversationServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[ConversationResponse]:
    entries = await service.inbox(current_user, limit)
    return [
        ConversationResponse.from_inbox(entry, current_user.uid) for entry in entries
    ]


@router.post(
    "/{conversation_id}/messages",
    status_code=status.HTTP_201_CREATED,
    description="Sends a message (reply) to the conversation. Any participant: borrower, broker or officer.",
    responses={404: {"detail": "Conversation not found"}},
)
@limiter.limit("30/minute")
async def send_message(
    request: Request,
    conversation_id: str,
    data: MessageCreateBody,
    current_user: CurrentUserDep,
    service: ConversationServiceDep,
) -> MessageResponse:
    message = await service.send_message(current_user, conversation_id, data.text)
    return MessageResponse.from_message(message, current_user.uid)


@router.get(
    "/{conversation_id}/messages",
    description=(
        "Messages of a conversation, oldest first. Without `before` returns the latest page and marks the "
        "conversation as read; pass the `created_at` of the oldest message as `before` to load older ones."
    ),
    responses={404: {"detail": "Conversation not found"}},
)
@limiter.limit("120/minute")
async def list_messages(
    request: Request,
    conversation_id: str,
    current_user: CurrentUserDep,
    service: ConversationServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    before: datetime.datetime | None = None,
) -> list[MessageResponse]:
    messages = await service.read_messages(
        current_user, conversation_id, limit=limit, before=before
    )
    return [
        MessageResponse.from_message(message, current_user.uid) for message in messages
    ]
