from typing import Annotated

from fastapi import Depends

from src.conversations.repository import ConversationFirestoreRepository
from src.conversations.service import ConversationService
from src.firebase.dependencies import FirestoreDep
from src.loan_applications.repository import LoanApplicationFirestoreRepository
from src.users.repository import UserProfileFirestoreRepository


def get_conversation_service(db: FirestoreDep) -> ConversationService:
    return ConversationService(
        ConversationFirestoreRepository(db),
        LoanApplicationFirestoreRepository(db),
        UserProfileFirestoreRepository(db),
    )


ConversationServiceDep = Annotated[
    ConversationService, Depends(get_conversation_service)
]
