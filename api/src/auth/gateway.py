from fastapi.concurrency import run_in_threadpool

from firebase_admin import auth

from src.auth.models import AuthUserModel
from src.auth.enums import Role


class FirebaseAuthGateway:
    async def set_user_role(self, uid: str, role: Role) -> None:
        user_record = await run_in_threadpool(auth.get_user, uid)
        custom_claims = dict(user_record.custom_claims or {})
        custom_claims["role"] = role.value
        await run_in_threadpool(auth.set_custom_user_claims, uid, custom_claims)
    
    async def get_user_account(self, uid: str) -> AuthUserModel: 
        ...
        
    async def add_user_aacount(self, user: AuthUserModel) -> None:
        ...