from typing import Optional

from pydantic import BaseModel

from src.auth.enums import Role, SignInProvider


class CurrentUserModel(BaseModel):
    uid: str
    
    email: str
    email_verified: bool = False
    photo_url: Optional[str] = None
    
    sign_in_provider: SignInProvider
    
    role: Optional[Role] = None



class AuthUserModel(BaseModel):
    uid: str
    
    disabled: bool = False
    display_name: Optional[str] = None
    
    email: str
    email_verified: bool = False
    
    phone_number: Optional[str] = None
    photo_url: Optional[str] = None
    
    sign_in_provider: str
    role: Optional[str] = None
    
    tokens_valid_after_timestamp: int