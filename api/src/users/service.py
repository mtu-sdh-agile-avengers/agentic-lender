from src.auth.enums import UserRole
from src.auth.models import CurrentUserModel
from src.auth.ports import AuthGatewayPort
from src.users.exceptions import UserProfileNotFoundError
from src.users.models import UserProfileModel
from src.users.ports import UserProfileRepositoryPort


class UserService:
    def __init__(self, repo: UserProfileRepositoryPort, auth: AuthGatewayPort):
        self._repo = repo
        self._auth = auth

    async def get_profile(self, current_user: CurrentUserModel) -> UserProfileModel:
        profile = await self._repo.get_user_profile(current_user.uid)

        if profile is None:
            raise UserProfileNotFoundError(current_user.uid)

        return profile

    async def create_profile(
        self,
        current_user: CurrentUserModel,
        *,
        full_name: str | None = None,
        phone: str | None = None,
    ) -> UserProfileModel:
        profile = UserProfileModel(
            uid=current_user.uid,
            email=current_user.email,
            role=UserRole.BORROWER,
            full_name=full_name,
            phone=phone,
        )

        await self._repo.add_user_profile(profile)
        await self._auth.set_user_role(current_user.uid, profile.role)

        return profile
