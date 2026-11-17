from fastapi import status

from src.exceptions import ApiError


class UserAuthError(ApiError):
    """base exception class for user auth accounts (firebase auth)"""


class UnauthorizedError(UserAuthError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_401_UNAUTHORIZED, "Unauthorized", {"WWW-Authenticate": "Bearer"}
        )


class ForbiddenError(UserAuthError):
    def __init__(self) -> None:
        super().__init__(status.HTTP_403_FORBIDDEN, "Forbidden")
