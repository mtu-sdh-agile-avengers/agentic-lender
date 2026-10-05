# Dataset decision: property valuation model (AL-AI Engine)

**Jira:** ALG4-58 · **Author:** Pavlo · **Status:** decided

## Context

The AL-AI Engine needs an Automated Valuation Model (AVM) that estimates a fair
market price for an Irish residential property from the attributes a borrower
enters in AL-Mobile: county, floor area, bedrooms, property type and BER rating.
The Valuation Agent then compares that estimate against the seller's asking
price to compute a verified Loan-to-Value ratio and flag overvalued collateral.

Four datasets were proposed in the project brief. All four were downloaded and
profiled with `ai/ml/explore_dataset.py`; the generated profiles are in
`ai/ml/reports/`.

## Candidates at a glance

| Dataset | Rows | Price | Floor area | Beds | BER | Location | Verdict |
|---|---|---|---|---|---|---|---|
| Ireland House Properties 2024 (Daft.ie) | 14,289 | yes (asking) | yes | yes | yes | county + coordinates | **Selected for training** |
| Irish Property Price Register (PPR) | 804,233 | yes (sale) | band only, mostly empty | no | no | county + address | Supporting role |
| UK House Price 2015-2024 | 90,000 | yes (sale) | no | no | no | postcode + county | Rejected |
| Kaggle Loan Prediction | 614 | n/a | no | no | no | urban/rural flag | Rejected for valuation |

## Decision

Train the AVM on the **Daft.ie 2024** dataset. Use the **Property Price
Register** to validate the price level and as a future source for a county
price-trend feature. Reject the UK and Loan Prediction datasets for this model.

## Why Daft.ie

It is the only candidate where the target (price) and the predictive features
appear in the same table. Everything the mobile app asks the borrower for is
present: county, floor area in m², bedrooms, bathrooms, property type and BER.
It also carries latitude and longitude for 99.8% of listings, which turned out
to be the strongest location signal available (see model results below).

### Known problems in the raw data

| Problem | Scale | How we handle it |
|---|---|---|
| `Price` is text; "Price on Application" | 983 rows | Convert to numeric, drop non-numeric rows |
| `Site` rows are land, not dwellings | 2,713 rows | Keep dwelling types only |
| Northern Ireland counties (GBP, different market) | 6 counties | Drop Antrim, Armagh, Derry, Down, Fermanagh, Tyrone |
| Zero bedrooms (mostly sites) | 2,914 rows raw | Require bedrooms > 0 |
| Floor area out of range (max 1,821,087 m²) | 5.1% outliers | Keep 20-600 m², blank the rest and impute |
| Floor area missing | 19.0% | Median imputation + `area_known` flag |
| BER missing or `SI_666` (exemption code) | 22.0% + 843 rows | Treat as unknown, impute + `ber_known` flag |
| Duplicate listings (same coordinates and price) | 212 rows | Drop before the train/test split |

Unused columns: `Title`, `Area`, `Listing Views`, `Features` (35.8% missing,
free text) and `Date of Construction` (52.5% missing). `Features` is a candidate
for a later NLP experiment.

### Rows surviving cleaning

```
                      step  rows_left  removed
                  raw data      14289        0
    drop non-numeric price      13260     1029
       keep dwellings only      10975     2285
     drop Northern Ireland      10921       54
              bedrooms > 0      10724      197
    price 50,000-3,000,000      10652       72
drop rows with no location      10404      248
   drop duplicate listings      10192      212
```

10,192 usable rows: 8,153 for training, 2,039 held out for testing.

## Why the Property Price Register is supporting, not training, data

PPR records 804,233 genuine sale prices from 2010 onwards with date, address,
county and eircode, but it carries no bedrooms, no BER and only a coarse text
size band that is populated for new builds. A feature-based model cannot be
trained on it.

It is valuable for two other things.

**Validation.** `ai/ml/ppr_calibration.py` compares the median asking price per
county (Daft, dwellings only) against the median sale price per county (PPR,
full-market sales only, VAT added back to new builds). Most counties agree
within ±10%, with asking prices slightly *below* sale prices in the strongest
markets:

| County | Ask median | Sale median | Gap |
|---|---|---|---|
| Laois | €285,000 | €309,000 | -7.8% |
| Kildare | €400,000 | €430,000 | -7.0% |
| Cork | €345,000 | €360,000 | -4.2% |
| Dublin | €475,000 | €490,000 | -3.1% |
| Clare | €295,000 | €295,000 | 0.0% |
| Wexford | €352,500 | €299,000 | +17.9% |
| Waterford | €362,500 | €300,000 | +20.8% |
| Longford | €230,000 | €185,000 | +24.3% |
| Donegal | €285,000 | €190,000 | +50.0% |

Counties with fewer than 30 listings are excluded. Because the gap is not a
single national number, we do **not** apply a blanket calibration factor. The
outliers (Donegal, Longford, Waterford) likely reflect a different property mix
between listings and sales rather than a true market gap, and a fairer
comparison would group by bedroom count as well as county.

**Future feature.** Median sale price per county per quarter can be joined onto
the Daft rows as a market-trend feature (backlog ML-05, priority Could).

## Why the UK dataset is rejected

90,000 rows, but the only usable fields are price, date, postcode, property type
code (D/S/T/F/O) and administrative area. No floor area, no bedrooms, no BER, so
it cannot train the same model and cannot serve as a fallback for Daft.ie.
The product is also Irish, so UK sale prices would need justification we do not
have.

## Why the Loan Prediction dataset is rejected for this model

It solves a different problem: approving a loan applicant, not pricing a
property. At 614 rows it is also very small. Critically, it contains `Gender`,
`Married` and `Dependents` — protected characteristics that we must not train
on (backlog AGT-12 forbids protected attributes in agent inputs).

If an approval-likelihood score is added to the mobile dashboard later, those
three columns must be dropped first. The dataset is retained in the repository
notes as an ethics example for the report.

## Result with the chosen dataset

Four regression models trained on the cleaned Daft data, scored on the held-out
2,039 rows:

| Model | MAE | RMSE | MAPE | R² |
|---|---|---|---|---|
| Linear regression | €141,462 | €218,481 | 38.9% | 0.529 |
| Linear on log price | €120,836 | €217,883 | 28.3% | 0.532 |
| Random Forest | €92,108 | €177,350 | 23.1% | 0.690 |
| **Gradient boosting on log price** | **€86,649** | **€170,597** | **20.0%** | **0.713** |

Feature importance (Random Forest, used for interpretability): floor area 0.33,
longitude 0.21, county_Dublin 0.13, latitude 0.12, bedrooms 0.06, bathrooms
0.06, BER score 0.03. Coordinates together outweigh the county label, meaning
precise location carries more price signal than administrative boundaries.

## Limitations to state in the report

1. **Asking prices, not sale prices.** The model estimates what a property would
   be *listed* at. Outputs should be labelled "estimated market asking value".
2. **Accuracy is not production grade.** 20% average error on a €360,000 median
   price is roughly €72,000. This is why an underwriter signs off and the agent
   reports a range rather than a single figure.
3. **Error is concentrated in cheap rural stock.** Roughly 32% error in the
   cheapest fifth of the market versus about 11% in the middle.
4. **Single snapshot, no time dimension.** Listings are from 2024, so the model
   cannot capture price movement. PPR could supply that later.
5. **Missing data inflates estimates.** Properties with unknown floor area and
   BER receive higher predictions, which understates LTV. The API must validate
   that required fields are present rather than relying on imputation.

## Sources

- Ireland House Properties Dataset 2024: https://www.kaggle.com/datasets/adnankhalid007/ireland-house-properties-dataset-2024
- Irish Property Price Register: https://www.kaggle.com/datasets/fionnhughes/property-price-register
- UK House Price Prediction Dataset: https://www.kaggle.com/datasets/swarupsudulaganti/uk-house-price-prediction-dataset-2015-to2024
- Kaggle Loan Prediction Dataset: https://www.kaggle.com/datasets/altruistdelhite04/loan-prediction-problem-dataset

Profiles generated by `ai/ml/explore_dataset.py` are in `ai/ml/reports/`.
