from typing import Protocol

from src.reviews.models import ReviewModel


class ReviewRepositoryPort(Protocol):
    def next_id(self) -> str: ...
    async def add_review(self, review: ReviewModel) -> None: ...
