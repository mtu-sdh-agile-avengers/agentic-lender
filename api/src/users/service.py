import asyncio
from typing import Optional

from src.users.exceptions import UserProfileNotFoundError
from src.auth.ports import AuthGateway
from src.users.ports import UserProfileRepository
from src.users.models import UserProfileModel
from src.auth.models import CurrentUserModel
from src.auth.enums import Role


class UserService:
    def __init__(self, repo: UserProfileRepository, auth: AuthGateway):
        self._repo = repo
        self._auth = auth
    
    
    async def get_my_profile(self, current_user: CurrentUserModel) -> UserProfileModel:
        profile = await self._repo.get_user_profile(current_user.uid)
        
        if profile is None:
            raise UserProfileNotFoundError(current_user.uid)
        
        return profile
    
    async def create_my_profile(
        self, 
        current_user: CurrentUserModel,
        *,
        full_name: Optional[str] = None,
        phone: Optional[str] = None
    ) -> UserProfileModel:
        
        
        profile = UserProfileModel(
            uid=current_user.uid,
            email=current_user.email,
            role=Role.BORROWER,
            full_name=full_name,
            phone=phone
        )

        await self._repo.add_user_profile(profile)
        await self._auth.set_user_role(current_user.uid, profile.role)
        
        return profile