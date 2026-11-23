from fastapi.concurrency import run_in_threadpool
from firebase_admin import auth

from src.auth.enums import UserRole
from src.auth.models import AuthUserModel


class FirebaseAuthGateway:
    async def set_user_role(self, uid: str, role: UserRole) -> None:
        user_record = await run_in_threadpool(auth.get_user, uid)
        custom_claims = dict(user_record.custom_claims or {})
        custom_claims["role"] = role.value
        await run_in_threadpool(auth.set_custom_user_claims, uid, custom_claims)

    async def get_user_account(
        self, uid: str
    ) -> AuthUserModel: ...  # not required, since account could be obtained using Firebase Auth SDK, may be implemented in future

    async def add_user_account(
        self, user: AuthUserModel
    ) -> None: ...  # creation of the account using FirebaseAdminSDK is not required
