import datetime
from typing import Self

from pydantic import Field, field_validator

from src.reviews.models import MAX_COMMENT_LENGTH, MAX_RATING, MIN_RATING, ReviewModel
from src.schemas import BaseSchema


class ReviewCreateBody(BaseSchema):
    """Body of `POST /api/v1/reviews`."""

    rating: int = Field(ge=MIN_RATING, le=MAX_RATING, examples=[5])
    comment: str | None = Field(
        None, max_length=MAX_COMMENT_LENGTH, examples=["Quick answers from my broker"]
    )

    @field_validator("comment")
    @classmethod
    def _empty_means_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ReviewResponse(BaseSchema):
    review_id: str
    user_id: str
    rating: int
    comment: str | None
    created_at: datetime.datetime

    @classmethod
    def from_model(cls, model: ReviewModel) -> Self:
        return cls.model_validate(model.model_dump())
