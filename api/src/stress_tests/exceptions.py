from fastapi import status

from src.exceptions import ApiError


class StressTestError(ApiError):
    """base exception class for stress tests"""


class StressTestNotFoundError(StressTestError):
    def __init__(self, stress_test_id: str) -> None:
        super().__init__(
            status.HTTP_404_NOT_FOUND,
            f"Stress test (id: {stress_test_id}) is not found",
        )


class StressTestEmptyPortfolioError(StressTestError):
    def __init__(self) -> None:
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "The selected portfolio has no loan applications to stress",
        )
