import datetime
from typing import Optional

from pydantic import BaseModel, Field
from src.auth.enums import Role

def _utc_datettime_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)

class UserProfileModel(BaseModel):
    uid: str
    email: str
    phone: Optional[str] = None
    full_name: Optional[str]= None
    role: Role
    created_at: datetime.datetime = Field(default_factory=_utc_datettime_now)
    updated_at: datetime.datetime = Field(default_factory=_utc_datettime_now)

