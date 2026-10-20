from fastapi import HTTPException, status


class UnauthorizedException(HTTPException):
    def __init__(
        self,
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized",
        headers={"WWW-Authentificate": "Bearer"},
    ) -> None:
        super().__init__(status_code, detail, headers)


class ForbiddenException(HTTPException):
    def __init__(
        self, 
        status_code=status.HTTP_403_FORBIDDEN, 
        detail="Forbidden"
    ) -> None:
        super().__init__(status_code, detail)
