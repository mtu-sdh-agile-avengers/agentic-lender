from typing import Protocol

from src.auth.enums import UserRole
from src.auth.models import AuthUserModel


class AuthGatewayPort(Protocol):
    async def set_user_role(self, uid: str, role: UserRole) -> None: ...
    async def get_user_account(self, uid: str) -> AuthUserModel: ...
    async def add_user_account(self, user: AuthUserModel) -> None: ...
