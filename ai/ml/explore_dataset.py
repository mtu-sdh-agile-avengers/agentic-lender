"""
AL: Agentic Lender - dataset profiler (backlog task ML-01).

Point it at any CSV and it tells you what is inside: columns, types, missing
values, duplicates, outliers, and a suggested COLUMN_MAP for avm_baseline.py.
Use it to compare the candidate datasets and justify which one you pick.

Usage:
    pip install pandas numpy matplotlib
    python explore_dataset.py data/daft_ireland_2024.csv
    python explore_dataset.py data/ppr.csv --target price

Writes a markdown report and histograms to reports/<filename>/.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Words we expect in column names, mapped to the names our model uses.
# The profiler uses these to guess which column is which.
NAME_HINTS = {
    "price": ["price", "amount", "value", "sale", "cost"],
    "county": ["county", "region", "area", "location", "city", "town"],
    "floor_area_m2": ["floor", "area", "size", "sqm", "sq_m", "square", "m2"],
    "bedrooms": ["bed", "bedroom", "br"],
    "bathrooms": ["bath", "bathroom"],
    "property_type": ["type", "category", "dwelling", "propertytype"],
    "ber": ["ber", "energy", "epc", "rating"],
}


def to_md(frame: pd.DataFrame) -> str:
    """Markdown table if the tabulate package is installed, plain text if not."""
    try:
        return frame.to_markdown(index=False)
    except ImportError:
        return "```\n" + frame.to_string(index=False) + "\n```"


def load_csv(path: Path) -> pd.DataFrame:
    """Read a CSV, trying a second encoding if the default fails."""
    for encoding in ("utf-8", "latin-1"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError:
            print(f"  utf-8 failed, retrying with {encoding}")
    raise SystemExit(f"Could not read {path}")


def guess_columns(columns) -> dict:
    """Guess which real column matches each feature we need."""
    guesses = {}
    for target, hints in NAME_HINTS.items():
        for col in columns:
            normalised = str(col).lower().replace(" ", "_")
            if any(hint in normalised for hint in hints):
                guesses.setdefault(target, col)
    return guesses


def column_report(df: pd.DataFrame) -> pd.DataFrame:
    """One row per column: type, how much is missing, how varied it is."""
    rows = []
    for col in df.columns:
        series = df[col]
        missing_pct = series.isna().mean() * 100
        sample = series.dropna().unique()[:3]
        rows.append({
            "column": col,
            "dtype": str(series.dtype),
            "missing_%": round(missing_pct, 1),
            "unique": series.nunique(dropna=True),
            "examples": ", ".join(str(v)[:25] for v in sample),
        })
    return pd.DataFrame(rows)


def numeric_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Min / median / max and outlier count for numeric columns."""
    numeric = df.select_dtypes(include=np.number)
    if numeric.empty:
        return pd.DataFrame()

    rows = []
    for col in numeric.columns:
        series = numeric[col].dropna()
        if series.empty:
            continue
        # IQR rule: anything far outside the middle 50% is a suspected outlier
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = ((series < low) | (series > high)).sum()
        rows.append({
            "column": col,
            "min": round(series.min(), 2),
            "median": round(series.median(), 2),
            "max": round(series.max(), 2),
            "outliers": int(outliers),
            "outlier_%": round(outliers / len(series) * 100, 1),
        })
    return pd.DataFrame(rows)


def categorical_summary(df: pd.DataFrame, max_cols: int = 6) -> list:
    """Top values for text columns, so you can spot messy labels."""
    out = []
    text_cols = df.select_dtypes(include="object").columns[:max_cols]
    for col in text_cols:
        counts = df[col].value_counts().head(8)
        out.append((col, counts))
    return out


def save_histograms(df: pd.DataFrame, out_dir: Path) -> None:
    """Pictures beat tables when you are hunting for skew and outliers."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # no window needed, just save files
        import matplotlib.pyplot as plt
    except ImportError:
        print("  matplotlib not installed, skipping plots")
        return

    numeric = df.select_dtypes(include=np.number)
    for col in numeric.columns[:6]:
        series = numeric[col].dropna()
        if series.empty:
            continue
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.hist(series, bins=50)
        ax.set_title(f"{col} (n={len(series):,})")
        fig.tight_layout()
        fig.savefig(out_dir / f"hist_{col}.png", dpi=90)
        plt.close(fig)
    print(f"  histograms saved to {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile a CSV dataset")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--target", default=None,
                        help="name of the price column, if you already know it")
    args = parser.parse_args()

    if not args.csv_path.exists():
        sys.exit(f"File not found: {args.csv_path}")

    print(f"Reading {args.csv_path} ...")
    df = load_csv(args.csv_path)

    out_dir = Path("reports") / args.csv_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    duplicates = df.duplicated().sum()
    guesses = guess_columns(df.columns)
    if args.target:
        guesses["price"] = args.target

    cols = column_report(df)
    nums = numeric_summary(df)
    cats = categorical_summary(df)

    # ---- print to screen -------------------------------------------------
    print(f"\nRows: {len(df):,}   Columns: {len(df.columns)}   "
          f"Duplicate rows: {duplicates:,}")
    print("\nColumns:")
    print(cols.to_string(index=False))
    if not nums.empty:
        print("\nNumeric columns:")
        print(nums.to_string(index=False))
    for col, counts in cats:
        print(f"\nTop values in '{col}':")
        print(counts.to_string())

    print("\nSuggested COLUMN_MAP for avm_baseline.py (check it yourself!):")
    print("COLUMN_MAP = {")
    for target, source in guesses.items():
        print(f'    "{source}": "{target}",')
    print("}")

    missing_features = [t for t in NAME_HINTS if t not in guesses]
    if missing_features:
        print(f"\nNo column found for: {', '.join(missing_features)}")
        print("If 'price' or 'floor_area_m2' is missing, this dataset cannot "
              "train the valuation model on its own.")

    # ---- write the markdown report --------------------------------------
    report = [
        f"# Dataset profile: {args.csv_path.name}",
        "",
        f"- Rows: {len(df):,}",
        f"- Columns: {len(df.columns)}",
        f"- Duplicate rows: {duplicates:,}",
        "",
        "## Columns",
        "",
        to_md(cols),
    ]
    if not nums.empty:
        report += ["", "## Numeric columns", "", to_md(nums)]
    report += ["", "## Verdict", "",
               "_Fill this in: can this dataset train the AVM? What is missing?_"]

    report_path = out_dir / "profile.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(f"\nReport written to {report_path}")

    save_histograms(df, out_dir)


if __name__ == "__main__":
    main()