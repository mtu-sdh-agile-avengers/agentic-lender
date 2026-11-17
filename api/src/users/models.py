import datetime

from pydantic import BaseModel, Field

from src.auth.enums import UserRole


def _utc_datettime_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


class UserProfileModel(BaseModel):
    uid: str
    email: str
    phone: str | None = None
    full_name: str | None = None
    role: UserRole
    created_at: datetime.datetime = Field(default_factory=_utc_datettime_now)
    updated_at: datetime.datetime = Field(default_factory=_utc_datettime_now)
