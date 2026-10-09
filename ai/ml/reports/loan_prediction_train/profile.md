# Dataset profile: loan_prediction_train.csv

- Rows: 614
- Columns: 13
- Duplicate rows: 0

## Columns

| column            | dtype   |   missing_% |   unique | examples                     |
|:------------------|:--------|------------:|---------:|:-----------------------------|
| Loan_ID           | str     |         0   |      614 | LP001002, LP001003, LP001005 |
| Gender            | str     |         2.1 |        2 | Male, Female                 |
| Married           | str     |         0.5 |        2 | No, Yes                      |
| Dependents        | str     |         2.4 |        4 | 0, 1, 2                      |
| Education         | str     |         0   |        2 | Graduate, Not Graduate       |
| Self_Employed     | str     |         5.2 |        2 | No, Yes                      |
| ApplicantIncome   | int64   |         0   |      505 | 5849, 4583, 3000             |
| CoapplicantIncome | float64 |         0   |      287 | 0.0, 1508.0, 2358.0          |
| LoanAmount        | float64 |         3.6 |      203 | 128.0, 66.0, 120.0           |
| Loan_Amount_Term  | float64 |         2.3 |       10 | 360.0, 120.0, 240.0          |
| Credit_History    | float64 |         8.1 |        2 | 1.0, 0.0                     |
| Property_Area     | str     |         0   |        3 | Urban, Rural, Semiurban      |
| Loan_Status       | str     |         0   |        2 | Y, N                         |

## Numeric columns

| column            |   min |   median |   max |   outliers |   outlier_% |
|:------------------|------:|---------:|------:|-----------:|------------:|
| ApplicantIncome   |   150 |   3812.5 | 81000 |         50 |         8.1 |
| CoapplicantIncome |     0 |   1188.5 | 41667 |         18 |         2.9 |
| LoanAmount        |     9 |    128   |   700 |         39 |         6.6 |
| Loan_Amount_Term  |    12 |    360   |   480 |         88 |        14.7 |
| Credit_History    |     0 |      1   |     1 |         89 |        15.8 |

## Verdict

Rejected for the valuation model. This dataset predicts loan approval
(`Loan_Status`), not property price — there is no price target and no property
attributes beyond an urban/rural flag. At 614 rows it is also far too small.

It contains `Gender`, `Married` and `Dependents`, which are protected
characteristics we must not train on (AGT-12). If an approval-likelihood score
is added later, those three columns must be dropped first.

Kept as an ethics example for the report.