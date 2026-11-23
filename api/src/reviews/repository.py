from typing import Any

from src.enums import CollectionPath
from src.firebase.repository import FirestoreRepository
from src.reviews.models import ReviewModel


class ReviewFirestoreRepository(FirestoreRepository[ReviewModel]):
    col = CollectionPath.REVIEWS

    def _to_doc(self, entity: ReviewModel) -> dict[str, Any]:
        return entity.model_dump(exclude={"review_id"})

    def _from_doc(self, doc_id: str, data: dict[str, Any]) -> ReviewModel:
        return ReviewModel.model_validate({**data, "review_id": doc_id})

    def next_id(self) -> str:
        return (
            self._col_ref.document().id
        )  # generated locally by the SDK, no network call

    async def add_review(self, review: ReviewModel) -> None:
        await self._add(review.review_id, review)
