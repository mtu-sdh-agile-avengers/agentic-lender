import pandas as pd

DWELLINGS = ["Detached", "Semi-D", "Terrace", "End of Terrace",
             "Apartment", "Bungalow", "Townhouse", "Duplex", "Houses"]

# --- actual sale prices -------------------------------------------------
ppr = pd.read_parquet("data/property_price_register.parquet")
ppr = ppr[(~ppr.not_full_market_price) & (ppr.date_of_sale >= "2024-01-01")].copy()
ppr.loc[ppr.vat_exclusive, "price_eur"] *= 1.135      # add VAT back to new builds
ppr["county"] = ppr["county"].str.strip().str.title()
sold = ppr.groupby("county")["price_eur"].agg(sold_median="median", sold_n="size")

# --- asking prices, houses only -----------------------------------------
daft = pd.read_csv("data/daft_housing_data.csv")
daft["price"] = pd.to_numeric(daft["Price"], errors="coerce")
daft["beds"] = pd.to_numeric(daft["Number of Bedrooms"], errors="coerce")
daft["County"] = daft["County"].astype(str).str.strip().str.title()

homes = daft[daft["Property Type"].isin(DWELLINGS)
             & (daft["beds"] > 0)
             & daft["price"].notna()]
asked = homes.groupby("County")["price"].agg(ask_median="median", ask_n="size")

# --- compare ------------------------------------------------------------
cmp = asked.join(sold, how="inner")
cmp["gap_%"] = ((cmp.ask_median / cmp.sold_median - 1) * 100).round(1)
print(cmp[cmp.ask_n >= 30].sort_values("gap_%").to_string())

print(f"\nDaft rows: {len(daft)} -> {len(homes)} after filtering to dwellings")
print("Counties in Daft but not matched in PPR:",
      sorted(set(asked.index) - set(sold.index)))