from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "processed"


@dataclass(frozen=True)
class DatasetSpec:
    filename: str
    columns: tuple[str, ...]
    required_non_null: tuple[str, ...]
    key_columns: tuple[str, ...]
    expected_years: tuple[int, ...]
    validator: Callable[[pd.DataFrame], list[str]]


def _exact_years(*years: int) -> tuple[int, ...]:
    return tuple(years)


def _range_years(start: int, end: int) -> tuple[int, ...]:
    return tuple(range(start, end + 1))


def validate_combined_budget_summary(frame: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    unexpected_sections = sorted(set(frame["section"]) - {"balance", "revenue", "appropriation"})
    if unexpected_sections:
        errors.append(f"unexpected sections: {unexpected_sections}")

    if (frame["amount"] < 0).any():
        errors.append("contains negative amount values")

    latest = int(frame["fiscal_year"].max())
    required_rows = [
        (latest, "General Fund", "revenue", "TOTAL REVENUES"),
        (latest, "General Fund", "appropriation", "TOTAL APPROPRIATIONS"),
        (latest, "Total All Funds", "revenue", "TOTAL REVENUES"),
        (latest, "Total All Funds", "appropriation", "TOTAL APPROPRIATIONS"),
    ]
    for fiscal_year, fund, section, line_item in required_rows:
        mask = (
            (frame["fiscal_year"] == fiscal_year)
            & (frame["fund"] == fund)
            & (frame["section"] == section)
            & (frame["line_item"] == line_item)
        )
        if not mask.any():
            errors.append(
                f"missing latest-year total row for FY {fiscal_year}: {fund} / {section} / {line_item}"
            )

    return errors


def validate_acfr_budget_vs_actual(frame: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    tolerance = 100_000
    unexpected_sections = sorted(set(frame["section"]) - {"revenue", "expenditure"})
    if unexpected_sections:
        errors.append(f"unexpected sections: {unexpected_sections}")

    revenue = frame[frame["section"] == "revenue"]
    revenue_delta = ((revenue["actual"] - revenue["final_budget"]) - revenue["variance"]).abs()
    if (revenue_delta > tolerance).any():
        errors.append("revenue variance diverges from actual - final_budget by more than $100k")

    expenditure = frame[frame["section"] == "expenditure"]
    expenditure_delta = ((expenditure["final_budget"] - expenditure["actual"]) - expenditure["variance"]).abs()
    if (expenditure_delta > tolerance).any():
        errors.append("expenditure variance diverges from final_budget - actual by more than $100k")

    return errors


def validate_cip_categories(frame: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    if (frame["fy_amount"] < 0).any():
        errors.append("contains negative fy_amount values")

    with_multiyear = frame["multiyear_amount"].notna()
    if (frame.loc[with_multiyear, "multiyear_amount"] < frame.loc[with_multiyear, "fy_amount"]).any():
        errors.append("contains rows where multiyear_amount is less than fy_amount")

    latest = int(frame["fiscal_year"].max())
    latest_rows = frame[frame["fiscal_year"] == latest]
    if not latest_rows["category"].str.upper().eq("TOTAL").any():
        errors.append(f"missing Total row for FY {latest}")
    if latest_rows[~latest_rows["category"].str.upper().eq("TOTAL")].empty:
        errors.append(f"missing non-total category rows for FY {latest}")

    return errors


def validate_bond_status(frame: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    if (frame["authorized"] < 0).any():
        errors.append("contains negative authorized values")
    if frame["issued"].dropna().lt(0).any():
        errors.append("contains negative issued values")
    if frame["unissued"].dropna().lt(0).any():
        errors.append("contains negative unissued values")

    filled = frame.dropna(subset=["issued", "unissued"])
    if not filled.empty:
        delta = (filled["issued"] + filled["unissued"] - filled["authorized"]).abs()
        if (delta > 5_000_000).any():
            errors.append("issued + unissued diverges from authorized by more than $5M for at least one row")

    latest = int(frame["fiscal_year"].max())
    latest_rows = frame[frame["fiscal_year"] == latest]
    if not latest_rows["proposition"].str.upper().eq("TOTAL").any():
        errors.append(f"missing Total proposition row for FY {latest}")

    return errors


def validate_cip_revenue_sources(frame: pd.DataFrame) -> list[str]:
    errors: list[str] = []
    if (frame["fy_amount"] < 0).any():
        errors.append("contains negative fy_amount values")

    with_multiyear = frame["multiyear_amount"].notna()
    if (frame.loc[with_multiyear, "multiyear_amount"] < frame.loc[with_multiyear, "fy_amount"]).any():
        errors.append("contains rows where multiyear_amount is less than fy_amount")

    latest = int(frame["fiscal_year"].max())
    latest_rows = frame[frame["fiscal_year"] == latest]
    if not latest_rows["source"].str.upper().eq("TOTAL").any():
        errors.append(f"missing Total source row for FY {latest}")
    if latest_rows[~latest_rows["source"].str.upper().eq("TOTAL")].empty:
        errors.append(f"missing non-total revenue-source rows for FY {latest}")

    return errors


DATASET_SPECS: dict[str, DatasetSpec] = {
    "combined_budget_summary.csv": DatasetSpec(
        filename="combined_budget_summary.csv",
        columns=("section", "line_item", "amount", "fund", "fiscal_year"),
        required_non_null=("section", "line_item", "amount", "fund", "fiscal_year"),
        key_columns=("fiscal_year", "fund", "section", "line_item"),
        expected_years=_range_years(2008, 2026),
        validator=validate_combined_budget_summary,
    ),
    "acfr_budget_vs_actual.csv": DatasetSpec(
        filename="acfr_budget_vs_actual.csv",
        columns=("fiscal_year", "section", "line_item", "original_budget", "final_budget", "actual", "variance"),
        required_non_null=("fiscal_year", "section", "line_item", "original_budget", "final_budget", "actual", "variance"),
        key_columns=("fiscal_year", "section", "line_item"),
        expected_years=_range_years(2010, 2024),
        validator=validate_acfr_budget_vs_actual,
    ),
    "cip_categories.csv": DatasetSpec(
        filename="cip_categories.csv",
        columns=("category", "fy_amount", "multiyear_amount", "fiscal_year"),
        required_non_null=("category", "fy_amount", "fiscal_year"),
        key_columns=("fiscal_year", "category"),
        expected_years=_range_years(2008, 2026),
        validator=validate_cip_categories,
    ),
    "bond_status.csv": DatasetSpec(
        filename="bond_status.csv",
        columns=("bond_program", "proposition", "authorized", "issued", "unissued", "fiscal_year"),
        required_non_null=("bond_program", "proposition", "authorized", "fiscal_year"),
        key_columns=("fiscal_year", "bond_program", "proposition"),
        expected_years=_range_years(2015, 2026),
        validator=validate_bond_status,
    ),
    "cip_revenue_sources.csv": DatasetSpec(
        filename="cip_revenue_sources.csv",
        columns=("source", "fy_amount", "multiyear_amount", "fiscal_year"),
        required_non_null=("source", "fy_amount", "fiscal_year"),
        key_columns=("fiscal_year", "source"),
        expected_years=_exact_years(
            2011, 2012, 2013, 2014, 2015,
            2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026,
        ),
        validator=validate_cip_revenue_sources,
    ),
}


def validate_dataset(data_dir: Path, spec: DatasetSpec) -> list[str]:
    path = data_dir / spec.filename
    if not path.exists():
        return [f"missing file: {path}"]

    frame = pd.read_csv(path)
    errors: list[str] = []

    actual_columns = tuple(frame.columns)
    if actual_columns != spec.columns:
        errors.append(f"expected columns {list(spec.columns)} but found {list(actual_columns)}")
        missing_columns = [column for column in spec.columns if column not in frame.columns]
        if missing_columns:
            errors.append(f"missing expected columns: {missing_columns}")
            return errors

    missing_required = [column for column in spec.required_non_null if frame[column].isna().any()]
    if missing_required:
        errors.append(f"required columns contain nulls: {missing_required}")

    duplicate_count = int(frame.duplicated(list(spec.key_columns)).sum())
    if duplicate_count:
        errors.append(f"found {duplicate_count} duplicate primary-key rows for {list(spec.key_columns)}")

    actual_years = tuple(sorted(int(year) for year in frame["fiscal_year"].unique()))
    if actual_years != spec.expected_years:
        errors.append(f"expected fiscal years {list(spec.expected_years)} but found {list(actual_years)}")

    errors.extend(spec.validator(frame))
    return errors


def validate_all(data_dir: Path = DATA_DIR) -> dict[str, list[str]]:
    return {
        filename: errors
        for filename, spec in DATASET_SPECS.items()
        if (errors := validate_dataset(data_dir, spec))
    }


def main() -> None:
    failures = validate_all(DATA_DIR)
    if failures:
        lines = ["Dataset validation failed:"]
        for filename, errors in failures.items():
            lines.append(f"- {filename}")
            for error in errors:
                lines.append(f"  - {error}")
        raise SystemExit("\n".join(lines))

    for filename, spec in DATASET_SPECS.items():
        frame = pd.read_csv(DATA_DIR / filename)
        years = sorted(int(year) for year in frame["fiscal_year"].unique())
        print(f"{filename}: ok ({len(frame)} rows, FY {years[0]}-{years[-1]})")


if __name__ == "__main__":
    main()
