from src.loan_applications.models import UserInfoModel
from src.users.ports import UserProfileRepositoryPort


class UserInfoSearchGateway:
    """Adapter for `UserInfoSearchGatewayPort`, which utilizes UserProfileRepositoryPort."""

    def __init__(self, port: UserProfileRepositoryPort) -> None:
        self._port = port

    async def find_user(self, uid: str) -> UserInfoModel | None:
        profile = await self._port.get_user_profile(uid)

        if profile is None:
            return None

        return UserInfoModel(
            uid=profile.uid,
            full_name=profile.full_name,
            role=profile.role,
            email=profile.email,
            phone=profile.phone,
        )
