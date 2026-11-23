from datetime import datetime
from typing import Protocol

from conversations.models import ConversationModel, MessageModel


class ConversationRepositoryPort(Protocol):
    async def create_conversation(
        self, conversation: ConversationModel
    ) -> ConversationModel: ...
    async def get_conversation(
        self, conversation_id: str
    ) -> ConversationModel | None: ...
    async def get_conversations(
        self, participant_id: str, limit: int
    ) -> list[ConversationModel]: ...

    async def add_message(
        self, conversation: ConversationModel, message: MessageModel
    ) -> MessageModel: ...
    async def get_messages(
        self, conversation_id: str, limit: int, before: datetime.datetime | None = None
    ) -> list[MessageModel]: ...
    async def mark_read(self, conversation_id: str, participant_id: str) -> None: ...
