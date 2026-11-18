from typing import Protocol

from src.users.models import UserProfileModel


class UserProfileRepositoryPort(Protocol):
    async def add_user_profile(self, user_model: UserProfileModel) -> None: ...
    async def get_user_profile(self, uid: str) -> UserProfileModel | None: ...
