# AVM model results

Trained on 8,153 rows, tested on 2,039.

## Cleaning

                      step  rows_left  removed
                  raw data      14289        0
    drop non-numeric price      13260     1029
       keep dwellings only      10975     2285
     drop Northern Ireland      10921       54
              bedrooms > 0      10724      197
    price 50,000-3,000,000      10652       72
drop rows with no location      10404      248
   drop duplicate listings      10192      212

## Metrics

                   MAE_eur  RMSE_eur  MAPE_pct     R2
linear            141462.0  218481.0      38.9  0.529
linear_log_price  120836.0  217883.0      28.3  0.532
random_forest      92108.0  177350.0      23.1  0.690
hist_gb_log        86649.0  170597.0      20.0  0.713

Chosen model: **hist_gb_log**

## Feature importance (Random Forest)

               feature  importance
         floor_area_m2      0.3302
             longitude      0.2080
         county_Dublin      0.1329
              latitude      0.1178
              bedrooms      0.0647
             bathrooms      0.0625
             ber_score      0.0348
property_type_Detached      0.0096
             ber_known      0.0061
         county_Galway      0.0054
            area_known      0.0049
        county_Kildare      0.0049
