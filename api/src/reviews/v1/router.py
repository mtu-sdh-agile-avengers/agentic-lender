from fastapi import APIRouter, Request, status

from src.auth.dependencies import BorrowerDep
from src.rate_limiting import limiter
from src.reviews.dependencies import ReviewServiceDep
from src.reviews.v1.schemas import ReviewCreateBody, ReviewResponse

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


# POST /api/v1/reviews
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    description="Rates the service from 1 (worst) to 5 (best), with an optional comment (retail borrower).",
)
@limiter.limit("5/minute")
async def submit_review(
    request: Request,
    data: ReviewCreateBody,
    current_user: BorrowerDep,
    service: ReviewServiceDep,
) -> ReviewResponse:
    review = await service.submit(
        current_user, rating=data.rating, comment=data.comment
    )
    return ReviewResponse.from_model(review)
