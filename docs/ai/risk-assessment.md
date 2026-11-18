# Risk tier and approval chance (AL-AI Engine)

**Author:** Pavlo · **Status:** implemented (`risk-rules-v1`)

AL-AI Engine rates every mortgage application with a **risk tier** (`Low`,
`Medium`, `High`) and an **approval chance** in percent: how likely the
application is to be approved under our lending criteria.

The values of `tier` are exactly AL-Core's `RiskTier` enum, so AL-Core can
store them in `loan_applications.risk_tier` without mapping.

## Where to get it

| Endpoint | When | Speed |
|---|---|---|
| `POST /v1/risk-assessments` | On submission, to fill `risk_tier` straight away | Instant, no language model |
| `GET /v1/deliberations/{job_id}` → `result.risk` | With the committee result | When the run finishes |

Both use the same calculators, so they agree on the same application. Both
need the `X-Internal-Key` header, like every `/v1` endpoint.

`POST /v1/risk-assessments` takes the same body as `POST /v1/deliberations`
(`ApplicationInput`):

```json
{
  "application_id": "APP-001",
  "income": 85000,
  "existing_debt": 4000,
  "deposit": 50000,
  "loan": 300000,
  "asking_price": 350000,
  "rate_percent": 3.9,
  "term_years": 30,
  "first_time_buyer": true,
  "property": {
    "county": "Cork", "floor_area_m2": 110, "bedrooms": 3,
    "bathrooms": 2, "property_type": "Semi-D", "ber": "B2"
  }
}
```

Response (shortened):

```json
{
  "application_id": "APP-001",
  "risk": {
    "tier": "Medium",
    "score": 44,
    "approval_chance_percent": 80,
    "factors": [
      {"factor": "ltv", "label": "Loan-to-value", "value": 85.7, "unit": "%", "points": 18.6, "max_points": 25},
      {"factor": "lti", "label": "Loan-to-income", "value": 3.53, "unit": "x", "points": 17.2, "max_points": 25},
      {"factor": "dti", "label": "Stressed debt-to-income", "value": 29.8, "unit": "%", "points": 8.0, "max_points": 25},
      {"factor": "overvaluation", "label": "Asking price above estimate", "value": 0.0, "unit": "%", "points": 0.0, "max_points": 15},
      {"factor": "income_headroom", "label": "Income left after repayments", "value": 4971, "unit": "EUR/month", "points": 0.0, "max_points": 10}
    ],
    "hard_breaches": [],
    "ltv_basis": "asking price",
    "thresholds": {"medium_from": 35, "high_from": 65},
    "version": "risk-rules-v1",
    "note": "Estimated from lending criteria ..."
  },
  "affordability": {"dti_percent": 29.8, "lti_multiple": 3.53, "...": "..."},
  "collateral": {"ltv_percent": 85.7, "estimate": 350000, "...": "..."}
}
```

## How the score is built

Five factors add up to a risk score from 0 (safest) to 100. Each one is 0
points at the safe end and its maximum at the limit, linear in between.

| Factor | 0 points at | Full points at | Max |
|---|---|---|---|
| Loan-to-value | 60% | 90% (CBI limit) | 25 |
| Loan-to-income | 2.5x | CBI limit: 4x first-time buyers, 3.5x others | 25 |
| Stressed debt-to-income (rate + 2 points) | 25% | 40% (lender policy) | 25 |
| Asking price above the model estimate | 0% | 20% | 15 |
| Income left after repayments | €2,500 a month | €1,000 a month | 10 |

| Score | Tier |
|---|---|
| below 35 | Low |
| 35 to 64 | Medium |
| 65 and above | High |

A breached hard limit (LTV, LTI or stressed DTI) always gives `High`, a score
of at least 80 and an approval chance of at most 5%: such an application is
declined automatically by the committee.

**Approval chance.** The score goes through a logistic curve: about 92% at
the Low/Medium boundary, 50% at a score of 55 and about 22% at the
Medium/High boundary, never below 1% or above 99%. It is an estimate from our
criteria, not a probability learned from past loans: there is no repayment
history to learn one from. The committee's own decision (`result.decision`)
and the bank officer's decision are separate from it.

Limits are from the Central Bank of Ireland mortgage measures (in force since
1 January 2023) and lender policy; they live in `ai/app/agents/tools.py`, the
scoring in `ai/app/agents/risk.py`.

## For AL-Core

- On submit: `POST /v1/risk-assessments` with the application, then
  `risk_tier = RiskTier(response["risk"]["tier"])`. The response also has the
  approval chance and factors if the clients should show them.
- After a committee run: `result.risk` has the same shape; it can update
  `risk_tier` in `finish_assessment`.
- Counties must be one of the 26 names in `ai/app/counties.py` (the same as
  AL-Core's `County` enum). Case, extra spaces and a `Co.` prefix are
  accepted; anything else is a 422.
