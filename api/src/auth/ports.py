from typing import Protocol

from src.auth.models import AuthUserModel
from src.auth.enums import Role


class AuthGateway(Protocol):
    async def set_user_role(self, uid: str, role: Role) -> None: ...
    async def get_user_account(self, uid: str) -> AuthUserModel: ...
    async def add_user_aacount(self, user: AuthUserModel) -> None: ...