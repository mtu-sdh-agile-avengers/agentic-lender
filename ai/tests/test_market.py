"""Market & macro researcher (ALG4-83): ECB client, snapshot, committee, API.

No network: the ECB Data Portal is replaced by an httpx MockTransport that
answers in its SDMX-CSV format (`format=csvdata&detail=dataonly`).
"""

import httpx
import pytest
from fastapi.testclient import TestClient

from app.agents.graph import build_committee
from app.main import app
from app.services import market as market_module
from app.services.market import (
    DEPOSIT_RATE,
    EURIBOR_3M,
    MAIN_REFI_RATE,
    MORTGAGE_EA,
    MORTGAGE_IE,
    EcbClient,
    MarketDataError,
    build_snapshot,
    parse_csv,
    trend_of,
)

HEADER = "KEY,FREQ,REF_AREA,TIME_PERIOD,OBS_VALUE"
MONTHS = [f"2025-{m:02d}" for m in range(10, 13)] + [
    f"2026-{m:02d}" for m in range(1, 11)
]  # 13 months: Oct 2025 .. Oct 2026


def csv_for(series, rows):
    lines = [HEADER] + [f"{series.id},X,X,{period},{value}" for period, value in rows]
    return "\n".join(lines) + "\n"


def monthly(start, step):
    return [(period, round(start + i * step, 3)) for i, period in enumerate(MONTHS)]


RESPONSES = {
    DEPOSIT_RATE: csv_for(DEPOSIT_RATE, [("2026-11-20", "2.0")]),
    MAIN_REFI_RATE: csv_for(MAIN_REFI_RATE, [("2026-11-20", "2.15")]),
    EURIBOR_3M: csv_for(EURIBOR_3M, monthly(3.1, -0.09)),  # 3.10 -> 2.02
    MORTGAGE_IE: csv_for(MORTGAGE_IE, monthly(3.95, -0.03)),  # 3.95 -> 3.59
    MORTGAGE_EA: csv_for(MORTGAGE_EA, monthly(3.6, -0.02)),
}

APPLICATION = {
    "application_id": "APP-MKT",
    "income": 85_000,
    "existing_debt": 4_000,
    "deposit": 50_000,
    "loan": 300_000,
    "asking_price": 350_000,
    "rate_percent": 3.9,
    "term_years": 30,
    "property": {
        "county": "Cork",
        "floor_area_m2": 110,
        "bedrooms": 3,
        "bathrooms": 2,
        "property_type": "Semi-D",
        "ber": "B2",
    },
}


def fake_ecb(failing=(), calls=None):
    by_path = {
        f"/service/data/{s.flow}/{s.key}": (s, body) for s, body in RESPONSES.items()
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request.url.path)
        series, body = by_path.get(request.url.path, (None, None))
        if series is None or series in failing:
            return httpx.Response(404, text="No results found.")
        assert request.url.params["format"] == "csvdata"
        return httpx.Response(200, text=body)

    return httpx.MockTransport(handler)


def client_with(**kwargs):
    return EcbClient("https://data-api.example/service", transport=fake_ecb(**kwargs))


# --- parsing ---------------------------------------------------------------
def test_parse_csv_reads_period_and_value_oldest_first():
    text = f"{HEADER}\nK,X,X,2026-02,3.1\nK,X,X,2026-01,3.2\nK,X,X,2026-03,\n"
    assert [(o.period, o.value) for o in parse_csv(text)] == [
        ("2026-01", 3.2),
        ("2026-02", 3.1),
    ]


def test_parse_csv_rejects_an_unexpected_format():
    with pytest.raises(MarketDataError):
        parse_csv("<html>maintenance</html>")


def test_trend_thresholds():
    assert trend_of(0.3) == "rising"
    assert trend_of(-0.3) == "falling"
    assert trend_of(0.1) == "stable"
    assert trend_of(None) is None


# --- snapshot --------------------------------------------------------------
def test_snapshot_has_rates_trends_and_plain_facts():
    snapshot = build_snapshot(client_with(), offered_rate_percent=3.9)

    assert snapshot.available is True
    assert snapshot.ecb_deposit_rate.value_percent == 2.0
    assert snapshot.ecb_main_refinancing_rate.value_percent == 2.15
    assert snapshot.euribor_3m.trend == "falling"
    assert snapshot.euribor_3m.change_12m_points == pytest.approx(-1.08, abs=0.01)
    assert snapshot.mortgage_area == "Ireland"
    assert snapshot.mortgage_rate.value_percent == pytest.approx(3.59, abs=0.01)
    assert snapshot.mortgage_rate.as_of == "2026-10"
    assert snapshot.offered_vs_market_points == pytest.approx(0.31, abs=0.01)
    assert snapshot.errors == []
    assert any(
        "deposit facility rate is 2.00%" in fact for fact in snapshot.observations
    )
    assert any("in line with the market average" in f for f in snapshot.observations)
    assert snapshot.mortgage_rate.source_url.startswith("https://data.ecb.europa.eu/")


def test_rate_far_below_market_is_flagged():
    snapshot = build_snapshot(client_with(), offered_rate_percent=2.5)
    assert any("below the market average" in fact for fact in snapshot.observations)


def test_irish_series_missing_falls_back_to_euro_area():
    snapshot = build_snapshot(client_with(failing={MORTGAGE_IE}), 3.9)
    assert snapshot.mortgage_area == "euro area"
    assert snapshot.mortgage_rate.series == MORTGAGE_EA.id
    assert len(snapshot.errors) == 1


def test_ecb_down_means_unavailable_not_an_exception():
    everything = set(RESPONSES)
    snapshot = build_snapshot(client_with(failing=everything), 3.9)
    assert snapshot.available is False
    assert snapshot.observations == []
    assert len(snapshot.errors) == 5


def test_responses_are_cached_until_they_expire():
    calls, now = [], [0.0]
    client = EcbClient(
        "https://data-api.example/service",
        transport=fake_ecb(calls=calls),
        cache_seconds=60,
        clock=lambda: now[0],
    )
    client.observations(EURIBOR_3M, 13)
    client.observations(EURIBOR_3M, 13)
    assert len(calls) == 1
    now[0] = 61
    client.observations(EURIBOR_3M, 13)
    assert len(calls) == 2


# --- committee -------------------------------------------------------------
def test_committee_passes_market_facts_to_the_strategist():
    prompts = []

    def llm(prompt):
        prompts.append(prompt)
        return (
            '{"decision": "Approve", "conditions": [], "key_risks": [], "reason": "ok"}'
        )

    ecb = client_with()
    committee = build_committee(
        model_bundle=None, llm=llm, market=lambda rate: build_snapshot(ecb, rate)
    )
    final = committee.invoke({"application": APPLICATION, "trail": []})

    assert final["market"]["available"] is True
    assert final["market"]["mortgage_area"] == "Ireland"
    market_step = next(step for step in final["trail"] if step["agent"] == "market")
    assert "Euribor 3M" in market_step["summary"]
    assert "Average rate on new mortgages" in prompts[0]
    assert "source_url" not in prompts[0]  # facts only, not the links


def test_market_outage_does_not_stop_the_committee():
    def broken(_rate):
        raise RuntimeError("ECB unreachable")

    final = build_committee(model_bundle=None, llm=None, market=broken).invoke(
        {"application": APPLICATION, "trail": []}
    )
    assert final["market"]["available"] is False
    assert final["risk"]["tier"] in {"Low", "Medium", "High"}  # the run finished


# --- GET /v1/market --------------------------------------------------------
def test_market_endpoint_is_disabled_in_tests():
    with TestClient(app) as client:
        body = client.get("/v1/market").json()
    assert body["available"] is False
    assert "disabled" in body["errors"][0]


def test_market_endpoint_returns_the_snapshot(monkeypatch):
    ecb = client_with()
    monkeypatch.setattr(
        "app.routers.market.default_market_source",
        lambda: lambda rate: build_snapshot(ecb, rate),
    )
    with TestClient(app) as client:
        response = client.get("/v1/market", params={"rate_percent": 3.9})
    assert response.status_code == 200
    body = response.json()
    assert body["euribor_3m"]["trend"] == "falling"
    assert body["offered_rate_percent"] == 3.9


def test_market_endpoint_rejects_a_silly_rate():
    with TestClient(app) as client:
        assert client.get("/v1/market", params={"rate_percent": 80}).status_code == 422


def test_default_source_reuses_one_client(monkeypatch):
    """The ECB client (and its cache) is shared across runs."""
    monkeypatch.setattr(market_module, "_default_client", None)
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "market_data_enabled", True)
    market_module.default_market_source()
    first = market_module._default_client
    market_module.default_market_source()
    assert market_module._default_client is first
    first.close()
    monkeypatch.setattr(market_module, "_default_client", None)
