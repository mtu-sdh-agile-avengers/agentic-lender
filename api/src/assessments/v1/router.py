from fastapi import APIRouter, Request, status

from src.assessments.dependencies import AssessmentServiceDep
from src.assessments.v1.schemas import AssessmentResponse
from src.auth.dependencies import BrokerOrBankOfficerDep
from src.rate_limiting import limiter

router = APIRouter(
    prefix="/api/v1/loan-applications",
    tags=["assessments"],
)


# POST /api/v1/loan-applications/{loan_application_id}/assessments
@router.post(
    "/{loan_application_id}/assessments",
    status_code=status.HTTP_202_ACCEPTED,
    description=(
        "Starts an AI committee run (assigned broker or bank officer). Returns at once with status `queued`;"
        "poll `GET .../assessments/latest`. If a run is already in progress, that run is returned."
    ),
)
@limiter.limit("5/minute")
async def request_assessment(
    request: Request,
    loan_application_id: str,
    current_user: BrokerOrBankOfficerDep,
    service: AssessmentServiceDep,
) -> AssessmentResponse:
    view = await service.request_assessment(current_user, loan_application_id)
    return AssessmentResponse.from_view(view)


# GET /api/v1/loan-applications/{loan_application_id}/assessments/latest
@router.get(
    "/{loan_application_id}/assessments/latest",
    description=(
        "Get latest AI committee run: decision, each model's vote and reason, the agents' reasoning steps "
        "in order, and the verified figures (affordability, collateral, risk)."
    ),
)
@limiter.limit("60/minute")
async def get_latest_assessment(
    request: Request,
    loan_application_id: str,
    current_user: BrokerOrBankOfficerDep,
    service: AssessmentServiceDep,
) -> AssessmentResponse:
    view = await service.get_latest_assessment(current_user, loan_application_id)
    return AssessmentResponse.from_view(view)
