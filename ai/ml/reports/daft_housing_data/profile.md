# Dataset profile: daft_housing_data.csv

- Rows: 14,289
- Columns: 14
- Duplicate rows: 8

## Columns

| column               | dtype   |   missing_% |   unique | examples                                                                        |
|:---------------------|:--------|------------:|---------:|:--------------------------------------------------------------------------------|
| Title                | str     |         0.2 |    13907 | 'Horizons', Banna East, A, Ivella, Rectory Road, Enn, Grey's Corner, Ferrybank, |
| Price                | str     |         0.2 |      857 | 499000, 925000, 895000                                                          |
| Number of Bedrooms   | str     |         0   |       26 | 4, 5, 2                                                                         |
| Number of Bathrooms  | int64   |         0   |       20 | 6, 3, 2                                                                         |
| Property Type        | str     |         0.2 |       14 | Detached, End of Terrace, Semi-D                                                |
| Floor Area (m2)      | float64 |        19   |     1016 | 247.0, 262.0, 265.0                                                             |
| BER Rating           | str     |        22   |       21 | B3, SI_666, D1                                                                  |
| Latitude             | float64 |         0.2 |    13667 | 52.359776, 52.504937, 52.3486                                                   |
| Longitude            | float64 |         0.2 |    13684 | -9.797407, -6.562804, -6.456929                                                 |
| Listing Views        | float64 |         0.2 |     8851 | 3558.0, 5231.0, 14011.0                                                         |
| Area                 | str     |         2   |     1837 | banna-kerry, enniscorthy-wexford, ferrybank-wexford                             |
| County               | str     |         2   |       32 | Kerry, Wexford, Limerick                                                        |
| Features             | str     |        35.8 |     9059 | Sea/Mountain/Countryside , Exceptionally well-presen, Overlooking the River Sla |
| Date of Construction | float64 |        52.5 |      174 | 2007.0, 1978.0, 1983.0                                                          |

## Numeric columns

| column               |     min |   median |              max |   outliers |   outlier_% |
|:---------------------|--------:|---------:|-----------------:|-----------:|------------:|
| Number of Bathrooms  |    0    |     2    |     25           |        116 |         0.8 |
| Floor Area (m2)      |    0    |    98    |      1.82109e+06 |        592 |         5.1 |
| Latitude             |   51.46 |    53.29 |     55.33        |        265 |         1.9 |
| Longitude            |  -10.46 |    -7.7  |     -5.88        |          0 |         0   |
| Listing Views        |    0    |  4677    | 212933           |       1054 |         7.4 |
| Date of Construction | 1760    |  1990    |   2024           |        177 |         2.6 |

## Verdict

_Fill this in: can this dataset train the AVM? What is missing?_