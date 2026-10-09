# Dataset profile: UK_House_Price_Prediction_dataset_2015_to_2024.csv

- Rows: 90,000
- Columns: 11
- Duplicate rows: 43

## Columns

| column        | dtype   |   missing_% |   unique | examples                                     |
|:--------------|:--------|------------:|---------:|:---------------------------------------------|
| price         | int64   |           0 |     6111 | 735000, 160000, 176500                       |
| date          | str     |           0 |     2553 | 2017-08-07, 2023-02-03, 2015-01-06           |
| postcode      | str     |           0 |    75323 | LE17 5AP, SA11 4BD, ME3 0DQ                  |
| property_type | str     |           0 |        5 | D, T, S                                      |
| new_build     | str     |           0 |        2 | N, Y                                         |
| freehold      | str     |           0 |        2 | F, L                                         |
| street        | str     |           0 |    43483 | CLAYBROOKE COURT, GORED COTTAGES, GREEN LANE |
| locality      | str     |           0 |    10145 | CLAYBROOKE PARVA, MELINCOURT, ISLE OF GRAIN  |
| town          | str     |           0 |      958 | LUTTERWORTH, NEATH, ROCHESTER                |
| district      | str     |           0 |      359 | HARBOROUGH, NEATH PORT TALBOT, MEDWAY        |
| county        | str     |           0 |      117 | LEICESTERSHIRE, NEATH PORT TALBOT, MEDWAY    |

## Numeric columns

| column   |   min |   median |       max |   outliers |   outlier_% |
|:---------|------:|---------:|----------:|-----------:|------------:|
| price    |   100 |   244995 | 300000000 |       5219 |         5.8 |

## Verdict

Rejected. 90,000 rows, but no floor area, bedrooms or BER — only price, date,
postcode, property type code and administrative area. It cannot train the same
model and therefore cannot serve as a fallback for Daft.ie. The product is also
Irish, so UK sale prices would need justification we do not have.