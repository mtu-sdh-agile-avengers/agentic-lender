"""Valuation logic: request in, price estimate out (backlog ALG4-77 / ML-08).

Kept out of the router on purpose, so it can be unit-tested without HTTP and
reused by the Valuation Agent in the committee graph (ALG4-82).
"""

import json
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.schemas import (
    AskingPriceComparison,
    PriceRange,
    ValuationRequest,
    ValuationResponse,
)

CENTROIDS_PATH = Path(__file__).resolve().parent.parent / "data" / "county_centroids.json"

# A property is flagged when the asking price exceeds the estimate by this much
OVERVALUED_THRESHOLD_PCT = 10.0

# Fallback band when the saved model carries no metrics
DEFAULT_BAND_PCT = 20.0


@lru_cache
def county_centroids() -> dict[str, list[float]]:
    """Median coordinates per county, computed from the training data.

    The borrower only enters a county, but location is the model's second
    strongest signal, so we substitute the county's centre when exact
    coordinates are not supplied.
    """
    return json.loads(CENTROIDS_PATH.read_text(encoding="utf-8"))


def known_counties() -> list[str]:
    return sorted(county_centroids())


def build_feature_row(request: ValuationRequest, bundle: dict) -> tuple[pd.DataFrame, str]:
    """Turn the API request into the exact columns the pipeline expects."""
    centroids = county_centroids()
    if request.latitude is not None:
        latitude, longitude, source = request.latitude, request.longitude, "request"
    else:
        latitude, longitude = centroids[request.county]
        source = "county_centroid"

    ber_score = bundle["ber_score"].get(request.ber) if request.ber else None

    row = {name: float("nan") for name in
           bundle["numeric_features"] + bundle["categorical_features"]}
    row.update({
        "county": request.county,
        "property_type": request.property_type,
        "floor_area_m2": request.floor_area_m2,
        "bedrooms": request.bedrooms,
        "bathrooms": request.bathrooms,
        "latitude": latitude,
        "longitude": longitude,
        "ber_score": ber_score if ber_score is not None else float("nan"),
        "ber_known": int(ber_score is not None),
        "area_known": 1,
    })
    return pd.DataFrame([row]), source


def price_range(estimate: float, bundle: dict) -> PriceRange:
    """A band, not a single number: average error on test data was about 20%.

    Reporting one figure would imply precision the model does not have.
    """
    band = bundle.get("metrics", {}).get("MAPE_pct", DEFAULT_BAND_PCT)
    return PriceRange(
        low=int(round(estimate * (1 - band / 100), -3)),
        high=int(round(estimate * (1 + band / 100), -3)),
        basis=f"+/-{band:.0f}% (mean absolute percentage error on held-out data)",
    )


def compare_asking_price(estimate: float, asking: float) -> AskingPriceComparison:
    gap = (asking - estimate) / estimate * 100
    return AskingPriceComparison(
        asking_price=int(asking),
        gap_percent=round(gap, 1),
        overvalued=gap > OVERVALUED_THRESHOLD_PCT,
    )


def value_property(request: ValuationRequest, bundle: dict) -> ValuationResponse:
    features, coordinates_source = build_feature_row(request, bundle)
    estimate = float(bundle["model"].predict(features)[0])

    return ValuationResponse(
        estimate=int(round(estimate, -2)),
        range=price_range(estimate, bundle),
        model_version=bundle.get("version", "unknown"),
        coordinates_source=coordinates_source,
        ber_known=request.ber is not None,
        comparison=(compare_asking_price(estimate, request.asking_price)
                    if request.asking_price else None),
    )
