from typing import Optional, Protocol

from src.users.models import UserProfileModel


class UserProfileRepository(Protocol):
    async def get_user_profile(self, uid: str) -> Optional[UserProfileModel]: ...
    async def add_user_profile(self, user_model: UserProfileModel) -> None: ...
