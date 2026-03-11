from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.scrape_budgets import CANONICAL_FUND_LABELS


DATA_DIR = BASE_DIR / "data" / "processed"
REVENUE_PATH = DATA_DIR / "all_funds_revenue.csv"
COMBINED_PATH = DATA_DIR / "combined_budget_summary.csv"


def main() -> None:
    revenue = pd.read_csv(REVENUE_PATH)
    combined = pd.read_csv(COMBINED_PATH)

    required_columns = {
        "fund",
        "fund_raw",
        "line_item",
        "adopted_amount",
        "fiscal_year",
        "is_total_row",
    }
    missing = required_columns - set(revenue.columns)
    if missing:
        raise SystemExit(f"Missing required columns in {REVENUE_PATH.name}: {sorted(missing)}")

    bad_funds = sorted(set(revenue["fund"].dropna()) - CANONICAL_FUND_LABELS)
    if bad_funds:
        raise SystemExit(f"Unexpected canonical fund labels: {bad_funds}")

    unmapped = revenue[
        revenue["fund_raw"].fillna("").str.strip().ne("")
        & revenue["fund"].fillna("").str.strip().eq("")
    ]
    if not unmapped.empty:
        raise SystemExit(
            "Rows with raw fund labels but missing canonical fund values:\n"
            f"{unmapped[['fund_raw', 'line_item', 'fiscal_year']].to_string(index=False)}"
        )

    total_rows = revenue[revenue["is_total_row"]]
    latest = int(revenue["fiscal_year"].max())
    latest_total = total_rows[
        (total_rows["fiscal_year"] == latest)
        & (total_rows["fund"] == "General Fund")
        & (total_rows["line_item"].str.upper() == "TOTAL GENERAL FUND")
    ]
    latest_combined = combined[
        (combined["fiscal_year"] == latest)
        & (combined["fund"] == "General Fund")
        & (combined["line_item"] == "TOTAL REVENUES")
    ]

    if latest_total.empty or latest_combined.empty:
        raise SystemExit(f"Could not find latest-year General Fund total rows for FY {latest}")

    latest_revenue_total = float(latest_total.iloc[0]["adopted_amount"])
    latest_combined_total = float(latest_combined.iloc[0]["amount"])
    if latest_revenue_total != latest_combined_total:
        raise SystemExit(
            "Latest General Fund total does not match combined summary: "
            f"{latest_revenue_total} vs {latest_combined_total}"
        )

    print(f"Canonical fund labels: {sorted(CANONICAL_FUND_LABELS)}")
    print("Unmapped labels: 0")
    print(f"Latest General Fund total agrees with combined summary for FY {latest}")


if __name__ == "__main__":
    main()
