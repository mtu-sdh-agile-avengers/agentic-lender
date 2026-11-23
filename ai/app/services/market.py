"""Market & macro research for the credit committee (backlog ALG4-83).

Pulls the current euro-area base rates and the Irish mortgage benchmark from
the ECB Data Portal (official, free, no API key) and turns them into facts the
strategist can use:

    ECB deposit facility rate     FM   D.U2.EUR.4F.KR.DFR.LEV          daily
    ECB main refinancing rate     FM   D.U2.EUR.4F.KR.MRR_FR.LEV       daily
    3-month Euribor               FM   M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA monthly
    New mortgage rate, Ireland    MIR  M.IE.B.A2C.AM.R.A.2250.EUR.N    monthly
      fallback: euro area         MIR  M.U2.B.A2C.AM.R.A.2250.EUR.N

Like the other agents, no model does arithmetic: the latest values, their
12-month change and the trend are computed here. Responses are cached
(MARKET_CACHE_HOURS), so a busy day costs a handful of ECB calls. If the ECB
cannot be reached the committee still runs and the snapshot says
`available: false`.
"""

import csv
import io
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

PORTAL_URL = "https://data.ecb.europa.eu/data/datasets"
TREND_THRESHOLD_POINTS = 0.25  # a 12-month move smaller than this is "stable"
MARKET_VERSION = "ecb-v1"

Trend = Literal["rising", "falling", "stable"]


@dataclass(frozen=True)
class Series:
    flow: str
    key: str
    label: str

    @property
    def id(self) -> str:
        return f"{self.flow}.{self.key}"

    @property
    def portal_url(self) -> str:
        return f"{PORTAL_URL}/{self.flow}/{self.id}"


DEPOSIT_RATE = Series("FM", "D.U2.EUR.4F.KR.DFR.LEV", "ECB deposit facility rate")
MAIN_REFI_RATE = Series("FM", "D.U2.EUR.4F.KR.MRR_FR.LEV", "ECB main refinancing rate")
EURIBOR_3M = Series("FM", "M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA", "3-month Euribor")
MORTGAGE_IE = Series(
    "MIR", "M.IE.B.A2C.AM.R.A.2250.EUR.N", "New mortgage rate, Ireland"
)
MORTGAGE_EA = Series(
    "MIR", "M.U2.B.A2C.AM.R.A.2250.EUR.N", "New mortgage rate, euro area"
)


@dataclass(frozen=True)
class Observation:
    period: str  # "2026-10" (monthly) or "2026-11-20" (daily)
    value: float


class MarketDataError(Exception):
    """The ECB answered with something we cannot use."""


# ---------------------------------------------------------------------------
# ECB Data Portal client
# ---------------------------------------------------------------------------
class EcbClient:
    """Reads series from the ECB Data Portal SDMX API as CSV, with a TTL cache."""

    def __init__(
        self,
        base_url: str = "https://data-api.ecb.europa.eu/service",
        *,
        timeout: float = 5.0,
        cache_seconds: float = 6 * 3600,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"Accept": "text/csv"},
        )
        self._cache_seconds = cache_seconds
        self._clock = clock
        self._cache: dict[tuple[str, int], tuple[float, list[Observation]]] = {}
        self._lock = threading.Lock()

    def observations(self, series: Series, last: int) -> list[Observation]:
        """The last `last` observations of a series, oldest first."""
        cache_key = (series.id, last)
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached and cached[0] > self._clock():
                return cached[1]

        response = self._http.get(
            f"/data/{series.flow}/{series.key}",
            params={
                "lastNObservations": last,
                "format": "csvdata",
                "detail": "dataonly",
            },
        )
        response.raise_for_status()
        observations = parse_csv(response.text)
        if not observations:
            raise MarketDataError(f"{series.id}: no observations")

        with self._lock:
            self._cache[cache_key] = (
                self._clock() + self._cache_seconds,
                observations,
            )
        return observations

    def close(self) -> None:
        self._http.close()


def parse_csv(text: str) -> list[Observation]:
    """SDMX-CSV from the ECB: one row per observation, TIME_PERIOD and OBS_VALUE."""
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or not {"TIME_PERIOD", "OBS_VALUE"} <= set(
        reader.fieldnames
    ):
        raise MarketDataError("unexpected CSV: no TIME_PERIOD / OBS_VALUE columns")

    observations = []
    for row in reader:
        value = (row.get("OBS_VALUE") or "").strip()
        if not value or value.upper() == "NAN":
            continue
        observations.append(Observation(row["TIME_PERIOD"].strip(), float(value)))
    return sorted(observations, key=lambda obs: obs.period)


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------
class RateFact(BaseModel):
    label: str
    value_percent: float
    as_of: str = Field(description="Period of the latest observation")
    change_12m_points: float | None = Field(
        None, description="Latest minus the value 12 months earlier (monthly series)"
    )
    trend: Trend | None = None
    series: str
    source_url: str


class MarketSnapshot(BaseModel):
    available: bool = Field(description="False when no ECB series could be read")
    ecb_deposit_rate: RateFact | None = None
    ecb_main_refinancing_rate: RateFact | None = None
    euribor_3m: RateFact | None = None
    mortgage_rate: RateFact | None = Field(
        None, description="Average rate on new mortgages (Ireland; euro area if not)"
    )
    mortgage_area: Literal["Ireland", "euro area"] | None = None
    offered_rate_percent: float | None = None
    offered_vs_market_points: float | None = Field(
        None, description="Offered rate minus the average new mortgage rate"
    )
    observations: list[str] = Field(
        default_factory=list, description="Plain-English facts for the strategist"
    )
    errors: list[str] = Field(default_factory=list)
    fetched_at: str
    version: str = MARKET_VERSION


def trend_of(change: float | None) -> Trend | None:
    if change is None:
        return None
    if change >= TREND_THRESHOLD_POINTS:
        return "rising"
    if change <= -TREND_THRESHOLD_POINTS:
        return "falling"
    return "stable"


def _fact(series: Series, observations: list[Observation], monthly: bool) -> RateFact:
    latest = observations[-1]
    change = None
    if monthly and len(observations) >= 13:
        change = round(latest.value - observations[-13].value, 2)
    return RateFact(
        label=series.label,
        value_percent=round(latest.value, 2),
        as_of=latest.period,
        change_12m_points=change,
        trend=trend_of(change),
        series=series.id,
        source_url=series.portal_url,
    )


def _describe_trend(fact: RateFact) -> str:
    if fact.change_12m_points is None:
        return ""
    direction = {"rising": "up", "falling": "down", "stable": "about flat"}[
        fact.trend or "stable"
    ]
    if fact.trend == "stable":
        return f", {direction} over 12 months"
    return f", {direction} {abs(fact.change_12m_points):.2f} points in 12 months"


def build_snapshot(
    client: EcbClient, offered_rate_percent: float | None
) -> MarketSnapshot:
    """Read every series it can; a failed series is reported, never raised."""
    errors: list[str] = []

    def read(series: Series, last: int, monthly: bool) -> RateFact | None:
        try:
            return _fact(series, client.observations(series, last), monthly)
        except (httpx.HTTPError, MarketDataError, ValueError) as exc:
            logger.warning("market data: %s unavailable: %s", series.id, exc)
            errors.append(f"{series.label}: {type(exc).__name__}")
            return None

    deposit = read(DEPOSIT_RATE, 1, monthly=False)
    main_refi = read(MAIN_REFI_RATE, 1, monthly=False)
    euribor = read(EURIBOR_3M, 13, monthly=True)
    mortgage, area = read(MORTGAGE_IE, 13, monthly=True), "Ireland"
    if mortgage is None:
        mortgage, area = read(MORTGAGE_EA, 13, monthly=True), "euro area"

    observations: list[str] = []
    if deposit:
        observations.append(
            f"ECB deposit facility rate is {deposit.value_percent:.2f}% "
            f"(as of {deposit.as_of})."
        )
    if euribor:
        observations.append(
            f"3-month Euribor was {euribor.value_percent:.2f}% in {euribor.as_of}"
            f"{_describe_trend(euribor)}."
        )
    if mortgage:
        observations.append(
            f"Average rate on new mortgages ({area}) was "
            f"{mortgage.value_percent:.2f}% in {mortgage.as_of}"
            f"{_describe_trend(mortgage)}."
        )

    gap = None
    if mortgage and offered_rate_percent is not None:
        gap = round(offered_rate_percent - mortgage.value_percent, 2)
        if gap <= -0.5:
            observations.append(
                f"The offered rate ({offered_rate_percent:.2f}%) is {abs(gap):.2f} "
                "points below the market average: check it is realistic, the "
                "stress test is only as good as the starting rate."
            )
        elif gap >= 0.5:
            observations.append(
                f"The offered rate ({offered_rate_percent:.2f}%) is {gap:.2f} points "
                "above the market average: the borrower may refinance away, "
                "and repayments are higher than they need to be."
            )
        else:
            observations.append(
                f"The offered rate ({offered_rate_percent:.2f}%) is in line with "
                "the market average."
            )

    return MarketSnapshot(
        available=any([deposit, main_refi, euribor, mortgage]),
        ecb_deposit_rate=deposit,
        ecb_main_refinancing_rate=main_refi,
        euribor_3m=euribor,
        mortgage_rate=mortgage,
        mortgage_area=area if mortgage else None,
        offered_rate_percent=offered_rate_percent,
        offered_vs_market_points=gap,
        observations=observations,
        errors=errors,
        fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


# ---------------------------------------------------------------------------
# What the committee and the API use
# ---------------------------------------------------------------------------
MarketSource = Callable[[float | None], MarketSnapshot]

_default_client: EcbClient | None = None
_default_lock = threading.Lock()


def unavailable(reason: str) -> MarketSnapshot:
    return MarketSnapshot(
        available=False,
        errors=[reason],
        fetched_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )


def default_market_source() -> MarketSource:
    """The ECB-backed source from settings, or a disabled one (tests, offline)."""
    from app.config import get_settings

    settings = get_settings()
    if not settings.market_data_enabled:
        return lambda _rate: unavailable("market data disabled (MARKET_DATA_ENABLED)")

    global _default_client
    with _default_lock:
        if _default_client is None:
            _default_client = EcbClient(
                settings.ecb_api_url,
                timeout=settings.market_timeout_seconds,
                cache_seconds=settings.market_cache_hours * 3600,
            )
    client = _default_client
    return lambda rate: build_snapshot(client, rate)
