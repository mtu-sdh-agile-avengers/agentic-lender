import datetime
from typing import Self

from src.schemas import BaseSchema
from src.auth.enums import UserRole, SignInProvider
from src.auth.models import CurrentUserModel
from src.users.models import UserProfileModel


class UserCreateBody(BaseSchema):
    """
    Body of `POST /api/v1/users/me`.

    Contains ONLY fields, that the end-user may set themselves. Therefore, uid, email, email_verified, sign_in_provider and role
    are NOT here, because the server takes them from the verified token (Firebase Auth) or decides them itself, etc.
    """

    full_name: str | None = None
    phone: str | None = None


class UserResponse(BaseSchema):
    """
    Response body of `GET /api/v1/users/me`, `POST /api/v1/users/me`.
    """

    # general
    uid: str

    # user account (firebase auth)
    email: str
    email_verified: bool = False
    photo_url: str | None = None
    sign_in_provider: SignInProvider

    # user profile (firestore)
    role: UserRole
    phone: str | None = None
    full_name: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    @classmethod
    def parse_from_user(
        cls, current_user: CurrentUserModel, user_profile: UserProfileModel
    ) -> Self:
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
            updated_at=user_profile.updated_at,
        )
