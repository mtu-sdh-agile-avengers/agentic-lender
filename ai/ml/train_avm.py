"""
AL: Agentic Lender - train the Automated Valuation Model (AVM).

Covers backlog tasks ML-02 (clean + features), ML-03 (baseline linear
regression), ML-04 (Random Forest) and ML-06 (save the chosen model).

Cleaning rules come from our own profiling of daft_housing_data.csv:
  - keep dwellings only (2,713 "Site" rows are empty land, not houses)
  - drop "Price on Application" rows (983 of them, no label to learn from)
  - drop Northern Ireland counties (different market, prices in GBP)
  - floor area must be between 20 and 600 m2 (max in raw data: 1,821,087)
  - BER "SI_666" means exempt, not a rating -> treat as unknown
  - drop duplicates and rows with no bedrooms

Usage:
    python train_avm.py
    python train_avm.py --quick     # smaller forest, faster run while testing
"""

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import (
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    r2_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_PATH = Path("data/daft_housing_data.csv")
MODEL_PATH = Path("models/avm_v1.joblib")
REPORT_PATH = Path("reports/model_metrics.md")
CLEAN_PATH = Path("data/daft_clean.csv")
RANDOM_STATE = 42

# Column names in the raw CSV -> names we use everywhere else
COLUMN_MAP = {
    "Price": "price",
    "County": "county",
    "Floor Area (m2)": "floor_area_m2",
    "Number of Bedrooms": "bedrooms",
    "Number of Bathrooms": "bathrooms",
    "Property Type": "property_type",
    "BER Rating": "ber",
    "Latitude": "latitude",
    "Longitude": "longitude",
}

# Property types that are actual homes. "Site" is land, so it is excluded.
DWELLINGS = ["Detached", "Semi-D", "Terrace", "End of Terrace", "Apartment",
             "Bungalow", "Townhouse", "Duplex", "Houses", "Studio"]

# Northern Ireland: different country, different currency
NORTHERN_IRELAND = ["Antrim", "Armagh", "Derry", "Londonderry", "Down",
                    "Fermanagh", "Tyrone"]

# BER letters to a score: A1 = 15 (most efficient) ... G = 1 (least)
BER_GRADES = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3",
              "D1", "D2", "E1", "E2", "F", "G"]
BER_SCORE = {grade: len(BER_GRADES) - i for i, grade in enumerate(BER_GRADES)}

NUMERIC_FEATURES = ["floor_area_m2", "bedrooms", "bathrooms", "ber_score",
                    "ber_known", "area_known", "latitude", "longitude"]
CATEGORICAL_FEATURES = ["county", "property_type"]
TARGET = "price"

MIN_PRICE, MAX_PRICE = 50_000, 3_000_000
MIN_AREA, MAX_AREA = 20, 600


# ---------------------------------------------------------------------------
# Cleaning
# ---------------------------------------------------------------------------
class CleaningLog:
    """Records how many rows each rule removes, for the report."""

    def __init__(self, start_rows: int):
        self.rows = [("raw data", start_rows, 0)]

    def step(self, name: str, df: pd.DataFrame) -> pd.DataFrame:
        removed = self.rows[-1][1] - len(df)
        self.rows.append((name, len(df), removed))
        return df

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["step", "rows_left", "removed"])


def clean_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = raw.rename(columns=COLUMN_MAP)
    df = df[[c for c in COLUMN_MAP.values() if c in df.columns]].copy()
    log = CleaningLog(len(df))

    # "499000" and "Price on Application" live in the same text column.
    # to_numeric turns the words into NaN, which we then drop.
    df["price"] = pd.to_numeric(
        df["price"].astype(str).str.replace(r"[^\d.]", "", regex=True),
        errors="coerce")
    df = log.step("drop non-numeric price", df.dropna(subset=["price"]))

    for col in ["bedrooms", "bathrooms", "floor_area_m2", "latitude", "longitude"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["county"] = df["county"].astype(str).str.strip().str.title()
    df["property_type"] = df["property_type"].astype(str).str.strip()

    df = log.step("keep dwellings only",
                  df[df["property_type"].isin(DWELLINGS)])
    df = log.step("drop Northern Ireland",
                  df[~df["county"].isin(NORTHERN_IRELAND)])
    df = log.step("bedrooms > 0", df[df["bedrooms"] > 0])
    df = log.step(f"price {MIN_PRICE:,}-{MAX_PRICE:,}",
                  df[df["price"].between(MIN_PRICE, MAX_PRICE)])

    # Floor area is 19% missing. Rather than lose those rows, blank out the
    # impossible values and let the pipeline fill gaps with the median.
    # area_known remembers which rows were guessed.
    bad_area = ~df["floor_area_m2"].between(MIN_AREA, MAX_AREA)
    df.loc[bad_area, "floor_area_m2"] = np.nan
    df["area_known"] = (~df["floor_area_m2"].isna()).astype(int)

    # BER: "SI_666" is an exemption code, not a rating -> unknown
    df["ber"] = df["ber"].astype(str).str.upper().str.strip()
    df["ber_score"] = df["ber"].map(BER_SCORE)
    df["ber_known"] = (~df["ber_score"].isna()).astype(int)

    df = log.step("drop rows with no location",
                  df.dropna(subset=["county", "latitude", "longitude"]))
    df = log.step("drop duplicate listings",
                  df.drop_duplicates(subset=["latitude", "longitude", "price"]))

    return df.reset_index(drop=True), log.to_frame()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def make_preprocessor(scale_free: bool = True) -> ColumnTransformer:
    """Fill gaps, then turn text columns into 0/1 columns.

    The imputer lives inside the pipeline on purpose: the API will get
    incomplete input too, and the saved model must handle it the same way.
    """
    numeric = Pipeline([("impute", SimpleImputer(strategy="median"))])
    categorical = OneHotEncoder(
        drop="first" if scale_free else None, handle_unknown="ignore",
        sparse_output=False)
    return ColumnTransformer([
        ("num", numeric, NUMERIC_FEATURES),
        ("cat", categorical, CATEGORICAL_FEATURES),
    ])


def build_models(quick: bool = False) -> dict:
    linear = Pipeline([
        ("prep", make_preprocessor()),
        ("reg", LinearRegression()),
    ])

    # Same model, but learns log(price). House prices are skewed and effects
    # are multiplicative ("Dublin is +40%"), which suits a log scale.
    linear_log = TransformedTargetRegressor(
        regressor=Pipeline([
            ("prep", make_preprocessor()),
            ("reg", LinearRegression()),
        ]),
        func=np.log, inverse_func=np.exp)

    # Random Forest: many decision trees averaged together. It finds
    # non-linear patterns a straight line cannot, e.g. that latitude matters
    # differently inside Dublin than in the west.
    forest = Pipeline([
        ("prep", make_preprocessor(scale_free=False)),
        ("reg", RandomForestRegressor(
            n_estimators=100 if quick else 300,
            min_samples_leaf=2,
            n_jobs=-1,
            random_state=RANDOM_STATE)),
    ])

    boosted_log = TransformedTargetRegressor(
        regressor=Pipeline([
            ("prep", make_preprocessor(scale_free=False)),
            ("reg", HistGradientBoostingRegressor(random_state=RANDOM_STATE)),
        ]),
        func=np.log, inverse_func=np.exp)

    return {"linear": linear, "linear_log_price": linear_log,
            "random_forest": forest, "hist_gb_log": boosted_log}


def evaluate(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    pred = model.predict(X_test)
    return {
        "MAE_eur": mean_absolute_error(y_test, pred),
        "RMSE_eur": np.sqrt(mean_squared_error(y_test, pred)),
        "MAPE_pct": mean_absolute_percentage_error(y_test, pred) * 100,
        "R2": r2_score(y_test, pred),
    }


def show_importances(forest: Pipeline, top_n: int = 12) -> pd.DataFrame:
    """Which features the forest actually relies on."""
    names = forest.named_steps["prep"].get_feature_names_out()
    importances = forest.named_steps["reg"].feature_importances_
    frame = (pd.DataFrame({"feature": [n.split("__", 1)[1] for n in names],
                           "importance": importances})
             .sort_values("importance", ascending=False)
             .head(top_n)
             .reset_index(drop=True))
    frame["importance"] = frame["importance"].round(4)
    return frame


def value_property(bundle: dict, asking_price: float, **features) -> None:
    """What the Valuation Agent will do for every application."""
    row = {f: np.nan for f in NUMERIC_FEATURES + CATEGORICAL_FEATURES}
    row.update(features)
    row["ber_score"] = BER_SCORE.get(str(features.get("ber", "")).upper(), np.nan)
    row["ber_known"] = int(not np.isnan(row["ber_score"]))
    row["area_known"] = int(not pd.isna(features.get("floor_area_m2", np.nan)))

    estimate = float(bundle["model"].predict(pd.DataFrame([row]))[0])
    gap = (asking_price - estimate) / estimate * 100
    verdict = ("OVERVALUED, flag for review" if gap > 10
               else "below estimate" if gap < -10 else "within fair range")

    print("\nExample valuation")
    print(f"  Estimate:     EUR {estimate:,.0f}")
    print(f"  Asking price: EUR {asking_price:,.0f}  ({gap:+.1f}%, {verdict})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true",
                        help="smaller forest, faster run")
    args = parser.parse_args()

    if not DATA_PATH.exists():
        raise SystemExit(f"Not found: {DATA_PATH}")

    raw = pd.read_csv(DATA_PATH, low_memory=False)
    df, cleaning_log = clean_data(raw)

    print("Cleaning log")
    print(cleaning_log.to_string(index=False))
    print(f"\nUsable rows: {len(df):,}")
    print(f"Median price: EUR {df[TARGET].median():,.0f}")
    print(f"Floor area known: {df['area_known'].mean():.0%}   "
          f"BER known: {df['ber_known'].mean():.0%}")

    X = df[NUMERIC_FEATURES + CATEGORICAL_FEATURES]
    y = df[TARGET]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE)
    print(f"Train rows: {len(X_train):,}   Test rows: {len(X_test):,}")

    results = {}
    models = build_models(quick=args.quick)
    for name, model in models.items():
        print(f"\nTraining {name} ...")
        model.fit(X_train, y_train)
        results[name] = evaluate(model, X_test, y_test)

    scores = pd.DataFrame(results).T.round(
        {"MAE_eur": 0, "RMSE_eur": 0, "MAPE_pct": 1, "R2": 3})
    print("\nResults on the held-out test set")
    print(scores.to_string())

    best_name = scores["MAE_eur"].idxmin()
    best_model = models[best_name]
    print(f"\nBest model by MAE: {best_name}")

    importances = show_importances(models["random_forest"])
    print("\nWhat the forest relies on")
    print(importances.to_string(index=False))

    bundle = {
        "model": best_model,
        "version": f"{best_name}-v1",
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "ber_score": BER_SCORE,
        "metrics": results[best_name],
        "trained_rows": len(X_train),
    }
    value_property(bundle, asking_price=450_000, county="Cork",
                   floor_area_m2=110, bedrooms=3, bathrooms=2,
                   property_type="Semi-D", ber="B2",
                   latitude=51.90, longitude=-8.47)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, MODEL_PATH)
    df.to_csv(CLEAN_PATH, index=False)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join([
        "# AVM model results", "",
        f"Trained on {len(X_train):,} rows, tested on {len(X_test):,}.", "",
        "## Cleaning", "", cleaning_log.to_string(index=False), "",
        "## Metrics", "", scores.to_string(), "",
        f"Chosen model: **{best_name}**", "",
        "## Feature importance (Random Forest)", "",
        importances.to_string(index=False), "",
    ]), encoding="utf-8")

    print(f"\nSaved model to {MODEL_PATH}")
    print(f"Saved metrics to {REPORT_PATH}")
    print(f"Saved cleaned data to {CLEAN_PATH}")


if __name__ == "__main__":
    main()