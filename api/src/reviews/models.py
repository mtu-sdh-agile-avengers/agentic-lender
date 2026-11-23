import datetime

from pydantic import BaseModel, Field

from src.utils import _get_utc_now

MIN_RATING = 1
MAX_RATING = 5
MAX_COMMENT_LENGTH = 256


class ReviewModel(BaseModel):
    """Rating and feedback about the service from a retail borrower (`reviews/{review_id}`); read-only once created."""

    review_id: str  # document name, not a field
    user_id: str
    rating: int = Field(ge=MIN_RATING, le=MAX_RATING)  # 1 (worst) to 5 (best)
    comment: str | None = Field(
        None, max_length=MAX_COMMENT_LENGTH
    )  # None if left empty
    created_at: datetime.datetime = Field(default_factory=_get_utc_now)
