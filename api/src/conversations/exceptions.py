from fastapi import HTTPException, status


class ConversationNotFoundError(HTTPException):
    def __init__(self, conversation_id: str) -> None:
        super().__init__(
            status.HTTP_404_NOT_FOUND, f"Conversation (id: {conversation_id}) not found"
        )


class NoStaffAssignedError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT,
            "No broker or bank officer is assigned to this application yet; messaging opens once one is",
        )


class EmptyMessageError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Message text must not be empty"
        )
