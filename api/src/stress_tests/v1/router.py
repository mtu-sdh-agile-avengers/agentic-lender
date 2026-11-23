from typing import Annotated

from fastapi import APIRouter, Query, Request, status

from src.auth.dependencies import BrokerOrBankOfficerDep
from src.rate_limiting import limiter
from src.stress_tests.dependencies import StressTestServiceDep
from src.stress_tests.v1.schemas import (
    StressTestCreateBody,
    StressTestListItemResponse,
    StressTestResponse,
)

router = APIRouter(
    prefix="/api/v1/stress-tests",
    tags=["stress-tests"],
)


# POST /api/v1/stress-tests
@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    description=(
        "Runs a scenario over the caller's portfolio: central bank rate shock (`rateShockBps`) and/or property "
        "market downturn (`priceChangePercent`). Shows which borrowers could no longer afford repayments or "
        "would be in negative equity. The run is saved."
    ),
)
@limiter.limit("10/minute")
async def run_stress_test(
    request: Request,
    data: StressTestCreateBody,
    current_user: BrokerOrBankOfficerDep,
    service: StressTestServiceDep,
) -> StressTestResponse:
    stress_test = await service.run(
        current_user,
        rate_shock_bps=data.rate_shock_bps,
        price_change_percent=data.price_change_percent,
        statuses=set(data.statuses) if data.statuses else None,
        loan_application_ids=data.loan_application_ids,
    )
    return StressTestResponse.from_model(stress_test)


# GET /api/v1/stress-tests
@router.get(
    "",
    response_model=list[StressTestListItemResponse],
    description="Returns the caller's previous stress tests, newest first (without per-borrower results).",
)
@limiter.limit("30/minute")
async def get_stress_tests(
    request: Request,
    current_user: BrokerOrBankOfficerDep,
    service: StressTestServiceDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
):
    runs = await service.get_mine(current_user, limit)
    return [StressTestListItemResponse.from_model(run) for run in runs]


# GET /api/v1/stress-tests/{stress_test_id}
@router.get(
    "/{stress_test_id}",
    response_model=StressTestResponse,
    description="Return one of the caller's stress tests with per-borrower results.",
)
@limiter.limit("30/minute")
async def get_stress_test(
    request: Request,
    stress_test_id: str,
    current_user: BrokerOrBankOfficerDep,
    service: StressTestServiceDep,
):
    return StressTestResponse.from_model(
        await service.get(current_user, stress_test_id)
    )
