from src.auth.models import CurrentUserModel
from src.reviews.models import ReviewModel
from src.reviews.ports import ReviewRepositoryPort


class ReviewService:
    def __init__(self, reviews: ReviewRepositoryPort) -> None:
        self._reviews = reviews

    async def submit(
        self, current_user: CurrentUserModel, *, rating: int, comment: str | None
    ) -> ReviewModel:
        """Saves a rating (1-5) and an optional comment about the service (ALG4-223).

        Args:
            current_user: retail borrower who sent the review.
            rating: 1 (worst) to 5 (best).
            comment: the review text; `None` if the borrower left it empty.

        Returns:
            ReviewModel: the saved review.
        """
        review = ReviewModel(
            review_id=self._reviews.next_id(),
            user_id=current_user.uid,
            rating=rating,
            comment=comment,
        )
        await self._reviews.add_review(review)
        return review
