import datetime
from typing import Self

from pydantic import Field, field_validator, model_validator

from src.schemas import BaseSchema
from src.support_tickets.enums import SupportTicketCategory, SupportTicketStatus
from src.support_tickets.models import MAX_DESCRIPTION_LENGTH, SupportTicketModel


class SupportTicketCreateBody(BaseSchema):
    """Body of `POST /api/v1/support-tickets`."""

    category: SupportTicketCategory
    description: str = Field(
        min_length=1,
        max_length=MAX_DESCRIPTION_LENGTH,
        examples=["I uploaded the wrong payslip"],
    )
    loan_application_id: str | None = Field(
        None,
        max_length=128,
        description="Required for the `loan_application` category; must be empty for the others",
    )

    @field_validator("description")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("description must not be empty")
        return value

    @model_validator(mode="after")
    def _application_only_for_its_category(self) -> Self:
        about_application = self.category == SupportTicketCategory.LOAN_APPLICATION
        if about_application and not self.loan_application_id:
            raise ValueError(
                "loanApplicationId is required for the loan_application category"
            )
        if not about_application and self.loan_application_id:
            raise ValueError(
                "loanApplicationId is allowed only for the loan_application category"
            )
        return self


class SupportTicketResponse(BaseSchema):
    support_ticket_id: str
    user_id: str
    category: SupportTicketCategory
    description: str
    loan_application_id: str | None
    status: SupportTicketStatus
    created_at: datetime.datetime
    resolved_at: datetime.datetime | None

    @classmethod
    def from_model(cls, model: SupportTicketModel) -> Self:
        return cls.model_validate(model.model_dump())
