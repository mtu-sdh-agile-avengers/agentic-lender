from typing import Annotated

from fastapi import Depends

from src.auth.gateway import FirebaseAuthGateway
from src.firebase.dependencies import FirestoreDep
from src.users.repository import UserProfileFirestoreRepository
from src.users.service import UserService


def get_user_service(db: FirestoreDep) -> UserService:
    return UserService(UserProfileFirestoreRepository(db), FirebaseAuthGateway())

UserServiceDep = Annotated[UserService, Depends(get_user_service)]