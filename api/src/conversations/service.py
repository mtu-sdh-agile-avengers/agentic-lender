import datetime
from dataclasses import dataclass

from src.auth.enums import UserRole
from src.auth.models import CurrentUserModel
from src.conversations.exceptions import (
    ConversationNotFoundError,
    EmptyMessageError,
    NoStaffAssignedError,
)
from src.conversations.models import MAX_MESSAGE_LENGTH, ConversationModel, MessageModel
from src.conversations.repository import ConversationFirestoreRepository
from src.loan_applications.access import has_view_access
from src.loan_applications.exceptions import LoanApplicationNotFoundError
from src.loan_applications.ports import LoanApplicationRepositoryPort
from src.users.models import UserProfileModel
from src.users.ports import UserProfileRepositoryPort


@dataclass(frozen=True)
class InboxEntry:
    """One inbox row: a conversation, the other participant, and whether the current user has unread messages."""

    conversation: ConversationModel
    other_participant: UserProfileModel | None
    unread: bool


class ConversationService:
    def __init__(
        self,
        repo: ConversationFirestoreRepository,
        applications: LoanApplicationRepositoryPort,
        users: UserProfileRepositoryPort,
    ) -> None:
        self._conversations = repo
        self._applications = applications
        self._users = users

    async def _participant_conversation(
        self, conversation_id: str, current_user: CurrentUserModel
    ) -> ConversationModel:
        """Cheks if current user is participant for that conversation raises ConversationNotFoundError if not, otherwise
        returns conversation itself.

        Args:
            conversation_id: ID of the conversation.
            current_user: current user, sender of the request.

        Raises:
            ConversationNotFoundError: if current user is not a participant of the conversation.
        """
        conversation = await self._conversations.get_conversation(conversation_id)

        if conversation is None or current_user.uid not in conversation.participant_ids:
            raise ConversationNotFoundError(conversation_id)

        return conversation

    async def open_conversation(
        self,
        current_user: CurrentUserModel,
        loan_application_id: str,
        *,
        with_officer: bool = False,
    ) -> ConversationModel:
        """Opens (i.e., creates) conversation about a loan application between its borrower and the staff member handling it (broker / bank officer).

        Args:
            with_officer: if True, then conversation will be opened with related officer, otherwise with broker.
            current_user: user who sent the request; must be able to view the application.
            loan_application_id: ID of the loan application the conversation is about.

        Returns:
            ConversationModel: the newly created conversation, or the existing one if it was opened before.

        Raises:
            LoanApplicationNotFoundError: if the application does not exist or the current user may not view it.
            NoStaffAssignedError: if neither a broker nor a bank officer is assigned to the application yet.
        """
        application = await self._applications.get_loan_application(loan_application_id)
        if application is None or not has_view_access(current_user, application):
            raise LoanApplicationNotFoundError(loan_application_id)

        staff_id = (
            application.bank_officer_id if with_officer else application.broker_id
        )
        if staff_id is None:
            raise NoStaffAssignedError

        staff_role = "officer" if with_officer else "broker"

        return await self._conversations.create_conversation(
            ConversationModel(
                id=f"{application.loan_application_id}_{staff_role}",  # e.g., app-1_broker & app-1_officer
                loan_application_id=application.loan_application_id,
                borrower_id=application.borrower_id,
                staff_id=staff_id,
                participant_ids=[application.borrower_id, staff_id],
            )
        )

    async def inbox(
        self, current_user: CurrentUserModel, limit: int = 50
    ) -> list[InboxEntry]:
        """Returns the user's inbox: conversations they take part in, most recent activity first.

        Profiles of the other participants are read in one batch (not one read per conversation), so the
        inbox can show who each conversation is with.

        Args:
            current_user:  user who sent the request; must be a participant of the conversation.
            limit: maximum number of conversations to return.

        Returns:
            list[InboxEntryModel]: at most `limit` entries, newest `last_message_at` first. Each entry holds
            the conversation, the other participant's profile (`None` if that profile does not exist) and
            whether the conversation has messages the current_user has not read yet.
        """
        conversations = await self._conversations.get_conversations(
            current_user.uid, limit
        )
        other_uids = [
            uid
            for c in conversations
            for uid in c.participant_ids
            if uid != current_user.uid
        ]
        profiles = await self._users.get_user_profiles(other_uids)

        return [
            InboxEntry(
                conversation=c,
                other_participant=next(
                    (
                        profiles[uid]
                        for uid in c.participant_ids
                        if uid != current_user.uid and uid in profiles
                    ),
                    None,
                ),
                unread=current_user.uid in c.unread_by,
            )
            for c in conversations
        ]

    async def read_messages(
        self,
        current_user: CurrentUserModel,
        conversation_id: str,
        *,
        limit: int = 50,
        before: datetime.datetime | None = None,
    ) -> list[MessageModel]:
        """Returns one page of a conversation's messages, oldest first (chat order).

        Without `before` the latest page is returned and the conversation is marked as read for the user
        (opening the thread means reading it). With `before`, older messages are returned for scrolling back
        through the history, and the read state is left unchanged.

        Args:
            current_user: user who sent the request; must be a participant of the conversation.
            conversation_id: ID of the conversation.
            limit: maximum number of messages to return.
            before: return only messages created before this moment (inclusive); pass the `created_at` of the oldest
                message already shown to load the previous page. `None` for the latest page.

        Returns:
            list[MessageModel]: at most `limit` messages, oldest first.

        Raises:
            ConversationNotFoundError: if the conversation does not exist or the user is not a participant.
        """
        conversation = await self._participant_conversation(
            conversation_id, current_user
        )
        messages = await self._conversations.get_messages(
            conversation_id, limit, before
        )

        if before is None and current_user.uid in conversation.unread_by:
            await self._conversations.mark_read(conversation_id, current_user.uid)

        return messages

    async def send_message(
        self, current_user: CurrentUserModel, conversation_id: str, text: str
    ) -> MessageModel:
        """Sends a message (or a reply) to a conversation on behalf of the current user.

        Surrounding whitespace is removed. The message is saved together with the conversation summary
        (last message preview and time), and the conversation becomes unread for every other participant.

        Args:
            current_user: user who sent the request; must be a participant of the conversation.
            conversation_id: ID of the conversation.
            text: message text; at most `MAX_MESSAGE_LENGTH` characters are kept.

        Returns:
            MessageModel: the saved message, including the ID generated by Firestore.

        Raises:
            ConversationNotFoundError: if the conversation does not exist or the user is not a participant.
            EmptyMessageError: if the text is empty or contains only whitespace.
        """
        conversation = await self._participant_conversation(
            conversation_id, current_user
        )
        text = text.strip()

        if not text:
            raise EmptyMessageError

        message = MessageModel(
            sender_id=current_user.uid,
            sender_role=current_user.role or UserRole.UNSPECIFIED,
            text=text[:MAX_MESSAGE_LENGTH],
        )
        return await self._conversations.add_message(conversation, message)
