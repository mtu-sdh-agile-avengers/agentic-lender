from typing import Annotated

from fastapi import Depends

from src.firebase.dependencies import FirestoreDep
from src.reviews.repository import ReviewFirestoreRepository
from src.reviews.service import ReviewService


def get_review_service(db: FirestoreDep) -> ReviewService:
    return ReviewService(ReviewFirestoreRepository(db))


ReviewServiceDep = Annotated[ReviewService, Depends(get_review_service)]
