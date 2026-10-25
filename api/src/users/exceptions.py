from fastapi import HTTPException, status


class UserProfileError(HTTPException):
    """base exception class for user profiles (firestore)"""

class UserProfileAlreadyExistsError(UserProfileError):
    def __init__(self, uid: str) -> None:
        super().__init__(status.HTTP_409_CONFLICT, f"User profile (uid: {uid}) already exists")

class UserProfileNotFoundError(UserProfileError):
    def __init__(self, uid: str) -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, f"User profile (uid: {uid}) not found")
