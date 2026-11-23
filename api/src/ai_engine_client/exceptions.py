from fastapi import status

from src.exceptions import ApiError


class AIEngineError(ApiError):
    """base exception class for AL-AI Engine errors; the client of AL-Core gets 503 unless stated otherwise"""

    def __init__(
        self, reason: str, status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE
    ) -> None:
        super().__init__(status_code, f"AI committee is unavailable ({reason})")


class AIEngineUnavailableError(AIEngineError):
    """network error, timeout or 5xx: worth trying again later"""


class AIEngineAuthError(AIEngineError):
    """401: INTERNAL_API_KEY of AL-Core and AL-AI Engine differ (configuration error, not a client error)"""

    def __init__(self, path: str) -> None:
        super().__init__(f"X-Internal-Key rejected on {path}; INTERNAL_API_KEY differs")


class AIEngineNotFoundError(AIEngineError):
    """404: e.g. an unknown deliberation job (AL-AI Engine keeps jobs in memory, so a restart loses them)"""

    def __init__(self, path: str) -> None:
        super().__init__(f"nothing found on {path}")


class AIEngineRejectedError(AIEngineError):
    """4xx (e.g. 422): AL-Core sent data the engine does not accept; a bug on our side, so 502 Bad Gateway"""

    def __init__(self, path: str, status_code: int, detail: object) -> None:
        super().__init__(
            f"{status_code} on {path}: {detail}",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )
