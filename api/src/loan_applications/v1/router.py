from typing import Annotated

from fastapi import APIRouter, Request, status
from fastapi.params import Query

from src.auth.dependencies import (
    AnyRoleDep,
    BankOfficerDep,
    BorrowerDep,
    BrokerDep,
    BrokerOrBankOfficerDep,
)
from src.auth.enums import UserRole
from src.loan_applications.dependencies import LoanApplicationServiceDep
from src.loan_applications.v1.schemas import (
    BankOfficerAssignBody,
    LoanApplicationCreateBody,
    LoanApplicationFilterQuery,
    LoanApplicationResponse,
    LoanFileResponse,
    UnderwritingDecisionCreateBody,
)
from src.rate_limiting import limiter
from src.schemas import PaginatedResponse

router = APIRouter(
    prefix="/api/v1/loan-applications",
    tags=["loan-applications"],
)


# POST /api/v1/loan-applications
@router.post(
    "",
    response_model=LoanApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    description="Submits a new loan application (retail borrower).",
)
@limiter.limit("5/minute")
async def submit_loan_application(
    request: Request,
    data: LoanApplicationCreateBody,
    current_user: BorrowerDep,
    service: LoanApplicationServiceDep,
):
    application = await service.submit(
        current_user=current_user,
        broker_id=data.broker_id,
        annual_gross_income=data.annual_gross_income,
        annual_debt_repayments=data.annual_debt_repayments,
        deposit=data.deposit,
        term_years=data.term_years,
        first_time_buyer=data.first_time_buyer,
        property_spec=data.property_spec.to_model(),
    )
    return LoanApplicationResponse.from_model(application)


# GET /api/v1/loan-applications
@router.get(
    "",
    response_model=PaginatedResponse[LoanApplicationResponse],
    description="Returns loan applications of the caller, newest first.",
)
@limiter.limit("60/minute")
async def get_loan_applications_list(
    request: Request,
    filters: Annotated[LoanApplicationFilterQuery, Query()],
    current_user: AnyRoleDep,
    service: LoanApplicationServiceDep,
):
    page = await service.get_all_with_filters(current_user, **filters.model_dump())

    return PaginatedResponse[LoanApplicationResponse].build(
        items=[LoanApplicationResponse.from_model(item) for item in page.items],
        page=page.page,
        page_size=page.page_size,
        total=page.total,
    )


# GET /api/v1/loan-applications/{loan_application_id}
@router.get(
    "/{loan_application_id}",
    response_model=LoanFileResponse,
    description=(
        "Returns the loan file (dossier) of an application: financials, property, status history, the "
        "borrower's contact details, attached documents and a summary of the latest AI committee run. "
        "403 if the application is not one of the caller's (referred clients for a broker, portfolio for "
        "a bank officer, own applications for a borrower); 404 if it does not exist."
    ),
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "Not one of the caller's applications"
        },
        status.HTTP_404_NOT_FOUND: {"description": "Loan application does not exist"},
    },
)
@limiter.limit("60/minute")
async def get_loan_application(
    request: Request,
    loan_application_id: str,
    current_user: AnyRoleDep,
    service: LoanApplicationServiceDep,
):
    view = await service.get_file(current_user, loan_application_id)
    return LoanFileResponse.from_view(view)


# PUT /api/v1/loan-applications/{loan_application_id}/broker
@router.put(
    "/{loan_application_id}/broker",
    response_model=LoanApplicationResponse,
    description="Allows mortgage brokers to assign themselves to an unclaimed loan application.",
)
@limiter.limit("10/minute")
async def claim_loan_application(
    request: Request,
    loan_application_id: str,
    current_user: BrokerDep,
    service: LoanApplicationServiceDep,
):
    application = await service.claim_by_broker(current_user, loan_application_id)
    return LoanApplicationResponse.from_model(application)


# DELETE /api/v1/loan-applications/{loan_application_id}/broker
@router.delete(
    "/{loan_application_id}/broker",
    response_model=LoanApplicationResponse,
    description="Allows assigned mortgage brokers return claimed loan application.",
)
@limiter.limit("10/minute")
async def release_broker(
    request: Request,
    loan_application_id: str,
    current_user: BrokerDep,
    service: LoanApplicationServiceDep,
):
    application = await service.release_assignee(
        current_user, loan_application_id, UserRole.BROKER
    )
    return LoanApplicationResponse.from_model(application)


# PUT /api/v1/loan-applications/{loan_application_id}/bank-officer
@router.put(
    "/{loan_application_id}/bank-officer",
    response_model=LoanApplicationResponse,
    description="Allows bank officer to be assigned by broker to an unclaimed (by bank officer) loan application.",
)
@limiter.limit("10/minute")
async def assign_bank_officer(
    request: Request,
    loan_application_id: str,
    data: BankOfficerAssignBody,
    current_user: BrokerDep,
    service: LoanApplicationServiceDep,
):
    application = await service.assign_bank_officer(
        current_user, loan_application_id, data.bank_officer_id
    )
    return LoanApplicationResponse.from_model(application)


# DELETE /api/v1/loan-applications/{loan_application_id}/bank-officer
@router.delete(
    "/{loan_application_id}/bank-officer",
    response_model=LoanApplicationResponse,
    description="Allows bank officer to return loan application.",
)
@limiter.limit("10/minute")
async def release_bank_officer(
    request: Request,
    loan_application_id: str,
    current_user: BrokerOrBankOfficerDep,
    service: LoanApplicationServiceDep,
):
    application = await service.release_assignee(
        current_user, loan_application_id, UserRole.BANK_OFFICER
    )
    return LoanApplicationResponse.from_model(application)


# POST /api/v1/loan-applications/{loan_application_id}/decision
@router.post(
    "/{loan_application_id}/decision",
    response_model=LoanApplicationResponse,
    description="Allows assigned bank officer to make final lending decision (approve or decline) for loan application.",
)
@limiter.limit("10/minute")
async def make_decision(
    request: Request,
    loan_application_id: str,
    data: UnderwritingDecisionCreateBody,
    current_user: BankOfficerDep,
    service: LoanApplicationServiceDep,
):
    application = await service.make_decision(
        current_user=current_user,
        application_id=loan_application_id,
        outcome=data.outcome,
        reason=data.reason,
        conditions=data.conditions,
    )
    return LoanApplicationResponse.from_model(application)


# POST /api/v1/loan-applications/{loan_application_id}/withdrawal
@router.post(
    "/{loan_application_id}/withdrawal",
    response_model=LoanApplicationResponse,
    description="Allows borrower to withdraw (i.e., cancel) loan application if it's still open, before landing decision.",
)
@limiter.limit("10/minute")
async def withdraw_loan_application(
    request: Request,
    loan_application_id: str,
    current_user: BorrowerDep,
    service: LoanApplicationServiceDep,
):
    application = await service.withdraw(current_user, loan_application_id)
    return LoanApplicationResponse.from_model(application)
