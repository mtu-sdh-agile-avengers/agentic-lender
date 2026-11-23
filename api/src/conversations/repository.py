import datetime
from typing import Any, Optional, Protocol

from google.cloud.exceptions import Conflict
from google.cloud.firestore import ArrayRemove, AsyncCollectionReference, Query
from google.cloud.firestore_v1 import FieldFilter

from src.conversations.models import PREVIEW_LENGTH, ConversationModel, MessageModel
from src.enums import CollectionPath
from src.firebase.repository import FirestoreRepository


class ConversationFirestoreRepository(FirestoreRepository[ConversationModel]):
    col = CollectionPath.CONVERSATIONS

    def _to_doc(self, entity: ConversationModel) -> dict[str, Any]:
        return entity.model_dump(exclude={"id"})

    def _from_doc(self, doc_id: str, data: dict[str, Any]) -> ConversationModel:
        return ConversationModel.model_validate({**data, "id": doc_id})

    def _messages(self, conversation_id: str) -> AsyncCollectionReference:
        """Returns Firestore collection reference to the messages subcollection inside a conversation (found by id).

        Args:
            conversation_id: Conversation ID.

        Returns:
            Firestore collection reference of messages inside a conversation.
        """
        return self._col_ref.document(conversation_id).collection(
            CollectionPath.MESSAGES
        )

    async def create_conversation(
        self, conversation: ConversationModel
    ) -> ConversationModel:
        """Creates conversation between borrower, broker and/or bank officer.

        Args:
            conversation: Conversation model.

        Returns:
            ConversationModel: Created conversation OR existing one.
        """
        try:
            await self._add(conversation.id, conversation)
            return conversation
        except Conflict:
            existing = await self._get(conversation.id)
            assert existing is not None
            return existing

    async def get_conversation(self, conversation_id: str) -> ConversationModel | None:
        """Returns a conversation with specified ID.

        Args:
            conversation_id: Conversation ID.
        """
        return await self._get(conversation_id)

    async def get_conversations(
        self, participant_id: str, db_limit: int = 500, limit: int = 100
    ) -> list[ConversationModel]:
        """Returns list of conversation related to certain user (newest first).

        Args:
            participant_id: ID of the user.
            db_limit: limit to the amount of conversations found in Firestore.
            limit: slice up to db_limit conversations.

        Returns:
            list[ConversationModel]: list of conversation related to specified user.
        """
        query = self._col_ref.where(
            filter=FieldFilter("participant_ids", "array_contains", participant_id)
        )
        conversations = await self._stream(query.limit(db_limit))
        return sorted(conversations, key=lambda c: c.last_message_at, reverse=True)[
            :limit
        ]

    async def add_message(
        self, conversation: ConversationModel, message: MessageModel
    ) -> MessageModel:
        """Add message to the specified conversation.

        Args:
            conversation: Conversation model
            message: Message model.

        Returns:
            MessageModel: model of the new message.
        """
        message_ref = self._messages(conversation.id).document()
        recipients = [
            uid for uid in conversation.participant_ids if uid != message.sender_id
        ]

        batch = self._db.batch()
        batch.create(message_ref, message.model_dump(exclude={"id"}))
        batch.update(
            self._col_ref.document(conversation.id),
            {
                "last_message_preview": message.text[:PREVIEW_LENGTH],
                "last_sender_id": message.sender_id,
                "last_message_at": message.created_at,
                # the sender has obviously read the message; everyone else now has something unread
                "unread_by": recipients,
            },
        )
        await batch.commit()
        return message.model_copy(update={"id": message_ref.id})

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 100,
        before: datetime.datetime | None = None,
    ) -> list[MessageModel]:
        """Returns list of messages (newest first, with limit) related to specified conversation.

        Args:
            conversation_id: ID of the converstation.
            limit: limit to the amount of messages returned.
            before: date up to which message was created, used as a filter.

        Returns:
            list[MessageModel]: list of messages.
        """
        query = self._messages(conversation_id).order_by(
            "created_at", direction=Query.DESCENDING
        )
        if before is not None:
            query = query.where(filter=FieldFilter("created_at", "<=", before))
        newest_first = [
            MessageModel.model_validate(
                {**(doc_snap.to_dict() or {}), "id": doc_snap.id}
            )
            async for doc_snap in query.limit(limit).stream()
        ]
        return list(reversed(newest_first))

    async def mark_read(self, conversation_id: str, participant_id: str) -> None:
        """Marks existing message as red for specific participant.

        Args:
            conversation_id: ID of the conversation.
            participant_id: ID of the participant.
        """
        await self._update(
            conversation_id, {"unread_by": ArrayRemove([participant_id])}
        )
