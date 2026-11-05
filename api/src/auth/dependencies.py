"""Dependency functions (DI) for user authentication (identity) and authorization (access /rights).

Authorization: Bearer <Firebase ID token>
  1. bearer_token        reads the header (Authorization: Bearer <token>), does NOT validate anything
  2. verify_token        validates the token provided with the request (must be: unexpired, valid)
  3. get_current_user    gets CurrentUserModel (uid, email, role, ...) from verified claims of the token
  4. require_roles(...)  checks if the user's role allowed on protecetd route
  5. route handler
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from src.auth.models import CurrentUserModel
from src.auth.enums import Role, SignInProvider
from src.auth.exceptions import ForbiddenError, UnauthorizedError


bearer_token = HTTPBearer(auto_error=False)


def verify_token(
    token: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_token)],
) -> dict:
    """Uses HTTP bearer token to verify and decode JWT of the user (using Firebase Auth).
    Args:
        token: Bearer token; can be None.

    Returns:
        dict: Decoded Firebase Auth JWT of the user.

    Raises:
        UnauthorizedException: if the token is missing, invalid or expired.
    """
    if token is None:
        raise UnauthorizedError

    try:
        return auth.verify_id_token(token.credentials)
    except auth.InvalidIdTokenError as exc:
        raise UnauthorizedError from exc


def get_current_user(
    decoded_token: Annotated[dict, Depends(verify_token)],
) -> CurrentUserModel:
    """Builds the user who sent the request, from the verified token claims.

    Args:
        decoded_token: decoded JWT claims returned by verify_token.

    Returns:
        CurrentUserModel: pydantic model representing current user with uid, email, email_verified, role and auth_provider.
    """
    return CurrentUserModel(
        uid=decoded_token["uid"],
        
        email=decoded_token["email"],
        email_verified=decoded_token.get("email_verified", False),
        photo_url=decoded_token.get("photo_url", None),
        
        sign_in_provider=SignInProvider.parse(
            decoded_token.get("firebase", {}).get("sign_in_provider")
        ),
        
        role=Role.parse(decoded_token.get("role"))
    )
    
CurrentUserDep = Annotated[CurrentUserModel, Depends(get_current_user)]


def require_roles(
    *allowed_roles: Role,
) -> Callable[[CurrentUserModel], CurrentUserModel]:
    """Checks if the user have the permission to access protected route.

    Args:
        *allowed_roles: roles permitted on the route.

    Returns:
        Callable[[CurrentUserModel], CurrentUserModel]: Closure, allowing to protect routes with RBAC.

    Raises:
        ValueError: if no roles has been passed.
        ForbiddenException: if the users role is not allowed.
    """
    if not allowed_roles:
        raise ValueError("At least one role is required")

    def role_checker(
        current_user: Annotated[CurrentUserModel, Depends(get_current_user)],
    ) -> CurrentUserModel:
        if current_user.role not in allowed_roles:
            raise ForbiddenError
        return current_user

    return role_checker
