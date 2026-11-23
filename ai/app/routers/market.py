"""GET /v1/market - current rates from the ECB (backlog ALG4-83).

The same snapshot the committee's market agent uses: ECB deposit and main
refinancing rates, 3-month Euribor and the average rate on new Irish
mortgages, with 12-month trends. AL-Core can show it next to an application
or use it for rate-shock scenarios. Cached, so calling it often is cheap.
"""

from fastapi import APIRouter, Query

from app.deps import InternalAuth
from app.services.market import MarketSnapshot, default_market_source

router = APIRouter(prefix="/v1", tags=["market"], dependencies=[InternalAuth])


@router.get("/market", response_model=MarketSnapshot)
def get_market(
    rate_percent: float | None = Query(
        None,
        gt=0,
        le=25,
        description="Offered mortgage rate to compare with the market average",
    ),
) -> MarketSnapshot:
    """A plain `def`: FastAPI runs it in a worker thread, so ECB calls never
    block the event loop."""
    return default_market_source()(rate_percent)
