"""POST /v1/valuations - automated property valuation (backlog ALG4-77).

Called by AL-Core, which serves the fair-price checker in AL-Mobile and the
collateral assessment view in AL-Web. Never called directly by clients.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, status

from app.deps import InternalAuth, get_model
from app.schemas import ValuationRequest, ValuationResponse
from app.services.valuation import known_counties, value_property

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["valuations"], dependencies=[InternalAuth])


@router.get("/valuations/counties", response_model=list[str])
async def list_counties() -> list[str]:
    """Counties the model was trained on, for the dropdown in AL-Mobile."""
    return known_counties()


@router.post("/valuations", response_model=ValuationResponse,
             status_code=status.HTTP_200_OK)
async def create_valuation(request: ValuationRequest,
                           http_request: Request) -> ValuationResponse:
    """Estimate the market asking value of a property.

    Unknown counties are rejected rather than guessed: the model would still
    return a number, but it would be meaningless.

    The model is fetched inside the function, not as a dependency, so that a
    bad request is answered with 422 even when the model is missing.
    """
    if request.county not in known_counties():
        raise HTTPException(
            status_code=422,
            detail=f"unknown county '{request.county}'. "
                   f"Known counties: {', '.join(known_counties())}",
        )

    bundle = get_model(http_request)
    response = value_property(request, bundle)
    logger.info("valuation %s %s %sm2 -> EUR %s (%s)",
                request.county, request.property_type, request.floor_area_m2,
                response.estimate, response.model_version)
    return response
