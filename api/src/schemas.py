import math
from typing import Self, Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    """Base class for all schemas (allows to return JSON in `camelCase`). Inherits from BaseModel."""

    model_config = ConfigDict(
        alias_generator=to_camel,  # serializes model fields when `model_dump()` into `camelCase``
        validate_by_alias=True,  # allows to populate model by the alias
        validate_by_name=True,  # allows to populate model by the attribute name
    )


class QuerySchema(BaseSchema):
    """Base class for all query schemas (i.e., Query Parameter Models). Inherits from BaseSchema."""

    model_config = ConfigDict(validate_by_name=False, extra="forbid")


class PaginationQuery(QuerySchema):
    page: int = Field(1, ge=1, le=1000, description="page number (starting from 1)")
    page_size: int = Field(15, ge=1, le=100)


class PaginatedResponse[T](BaseSchema):
    items: list[T]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def build(
        cls, *, items: list[T], page: int, page_size: int, total: int
    ) -> PaginatedResponse[Any]:
        total_pages = math.ceil(total / page_size)
        return cls(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )
