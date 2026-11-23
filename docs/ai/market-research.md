# Market & macro researcher (AL-AI Engine)

**Jira:** ALG4-83 · **Author:** Pavlo · **Status:** implemented (`ecb-v1`)

The market agent gives the credit committee the current rate environment, so
the strategist does not judge an application in a vacuum. It reads official
statistics from the **ECB Data Portal**: free, no API key, no sign-up.

| Fact | ECB series | Frequency |
|---|---|---|
| ECB deposit facility rate | `FM.D.U2.EUR.4F.KR.DFR.LEV` | daily |
| ECB main refinancing rate | `FM.D.U2.EUR.4F.KR.MRR_FR.LEV` | daily |
| 3-month Euribor | `FM.M.U2.EUR.RT.MM.EURIBOR3MD_.HSTA` | monthly |
| Average rate on new mortgages, Ireland | `MIR.M.IE.B.A2C.AM.R.A.2250.EUR.N` | monthly |
| ... euro area, used if the Irish series fails | `MIR.M.U2.B.A2C.AM.R.A.2250.EUR.N` | monthly |

For the monthly series the agent computes the 12-month change and a trend
(`rising` / `falling` / `stable`, threshold 0.25 points), and compares the
application's offered rate with the average new-mortgage rate. Like the other
agents it does the arithmetic in Python; the strategist only gets the facts:

```json
{
  "available": true,
  "facts": [
    "ECB deposit facility rate is 2.00% (as of 2026-11-20).",
    "3-month Euribor was 2.02% in 2026-10, down 1.08 points in 12 months.",
    "Average rate on new mortgages (Ireland) was 3.59% in 2026-10, down 0.36 points in 12 months.",
    "The offered rate (3.90%) is in line with the market average."
  ],
  "offered_vs_market_points": 0.31
}
```

## Where it shows up

- **Committee result:** `result.market` (full snapshot with values, dates,
  trends, series IDs and links to the ECB portal) and a `market` step in the
  trail, e.g. `ECB deposit 2.00%, Euribor 3M 2.02% (falling), new mortgages
  3.59% (Ireland), offered +0.31 pts vs market`.
- **`GET /v1/market?rate_percent=3.9`:** the same snapshot on its own, for
  AL-Core (application page, rate-shock scenarios). Needs `X-Internal-Key`.

## Reliability

- Responses are cached for `MARKET_CACHE_HOURS` (6 by default): the ECB
  publishes these series daily or monthly, so a busy day costs a few calls.
- Each request times out after `MARKET_TIMEOUT_SECONDS` (5).
- A failed series is listed in `errors`; if none can be read the snapshot says
  `available: false` and the committee still runs on the calculators alone.
- `MARKET_DATA_ENABLED=false` switches it off (the tests do this and use
  recorded ECB responses instead).

## Checking it live

The development sandboxes could not reach `data-api.ecb.europa.eu`, so the
parser was built against the ECB's documented SDMX-CSV format. On a machine
with internet access:

```bash
curl "https://data-api.ecb.europa.eu/service/data/MIR/M.IE.B.A2C.AM.R.A.2250.EUR.N?lastNObservations=2&format=csvdata&detail=dataonly"
curl -H "X-Internal-Key: $INTERNAL_API_KEY" "http://localhost:8001/v1/market?rate_percent=3.9"
```

The second call should return `"available": true` with
`"mortgage_area": "Ireland"`. If it says `"euro area"`, the Irish series key
needs checking on the ECB portal (MIR dataset, reference area Ireland).
