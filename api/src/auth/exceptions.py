from fastapi import HTTPException, status


class UserAuthError(HTTPException):
    """base exception class for user auth accounts (firebase auth)"""

class UnauthorizedException(UserAuthError):
    def __init__(self) -> None:
        super().__init__(status.HTTP_401_UNAUTHORIZED, "Unauthorized", {"WWW-Authentificate": "Bearer"})

class ForbiddenException(UserAuthError):
    def __init__(self) -> None:
        super().__init__(status.HTTP_403_FORBIDDEN, "Forbidden")
