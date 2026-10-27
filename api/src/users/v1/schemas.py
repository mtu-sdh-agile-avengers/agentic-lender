import datetime
from typing import Optional, Self

from pydantic import BaseModel

from src.auth.models import CurrentUserModel
from src.users.models import UserProfileModel
from src.auth.enums import Role, SignInProvider

class UserCreate(BaseModel):
    """
    Body of `POST /api/v1/users/me`.

    Contains ONLY fields, that the end-user may set themself. Therefore, uid, email, email_verified, sign_in_provider and role
    are NOT here, becaused the server takes them from the verified token (Firebase Auth) or decides them itself, etc.
    """
    full_name: Optional[str] = None
    phone: Optional[str] = None


class UserResponse(BaseModel):
    """
    Response body of `GET /api/v1/users/me`, `POST /api/v1/users/me`.
    """
    # general
    uid: str
    
    # user account (firebase auth)
    email: str
    email_verified: bool = False
    photo_url: Optional[str] = None
    sign_in_provider: SignInProvider
    
    # user profile (firestore)
    role: Role
    phone: Optional[str] = None  
    full_name: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    @classmethod
    def parse_from_user(cls, current_user: CurrentUserModel, user_profile: UserProfileModel) -> Self:
        return cls(
            uid=user_profile.uid,
            
            email=current_user.email,
            email_verified=current_user.email_verified,
            photo_url=current_user.photo_url,
            sign_in_provider=current_user.sign_in_provider,
            
            role=user_profile.role,
            phone=user_profile.phone,
            full_name=user_profile.full_name,
            created_at=user_profile.created_at,
            updated_at=user_profile.updated_at
        )