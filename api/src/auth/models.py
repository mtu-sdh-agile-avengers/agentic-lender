from pydantic import BaseModel

from src.auth.enums import UserRole, SignInProvider


class CurrentUserModel(BaseModel):
    uid: str

    email: str
    email_verified: bool = False
    photo_url: str | None = None

    sign_in_provider: SignInProvider

    role: UserRole | None = None


class AuthUserModel(BaseModel):
    uid: str

    disabled: bool = False
    display_name: str | None = None

    email: str
    email_verified: bool = False

    phone_number: str | None = None
    photo_url: str | None = None

    sign_in_provider: str
    role: str | None = None

    tokens_valid_after_timestamp: int
