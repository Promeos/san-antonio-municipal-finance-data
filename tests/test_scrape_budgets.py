"""Tests for budget PDF scrapers — departments and revenue."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrape_budgets import (
    CANONICAL_FUND_LABELS,
    find_general_fund_summary_pages,
    find_all_funds_revenue_pages,
    normalize_fund_label,
    parse_general_fund_depts,
    parse_all_funds_revenue,
)


# ---------------------------------------------------------------------------
# Issue 1: Department scraper should not include non-department rows
# ---------------------------------------------------------------------------

class TestDepartmentFiltering:
    """parse_general_fund_depts should exclude tax-base and fund-balance rows."""

    GARBAGE_LABELS = [
        "TOTAL AVAILABLE FUNDS",
        "TOTAL TAXABLE VALUE",
        "Absolute Exemptions",
        "Over-65 Exemptions",
        "CURRENT PROPERTY TAX REVENUE",
    ]

    EXPECTED_DEPTS = ["Police", "Fire", "Parks"]

    def _run_parser(self, budget_pdf, fy):
        pdf = budget_pdf(fy)
        pages = find_general_fund_summary_pages(pdf)
        assert pages, f"No dept pages found for FY{fy}"
        return parse_general_fund_depts(pdf, pages, fy)

    def test_fy2024_no_garbage(self, budget_pdf):
        df = self._run_parser(budget_pdf, 2024)
        labels = df["department"].str.upper().tolist()
        for bad in self.GARBAGE_LABELS:
            assert bad.upper() not in labels, f"Found non-department row: {bad}"

    def test_fy2026_no_garbage(self, budget_pdf):
        df = self._run_parser(budget_pdf, 2026)
        labels = df["department"].str.upper().tolist()
        for bad in self.GARBAGE_LABELS:
            assert bad.upper() not in labels, f"Found non-department row: {bad}"

    def test_fy2024_has_real_depts(self, budget_pdf):
        df = self._run_parser(budget_pdf, 2024)
        labels_lower = df["department"].str.lower().tolist()
        for dept in self.EXPECTED_DEPTS:
            assert any(dept.lower() in l for l in labels_lower), (
                f"Missing expected department: {dept}"
            )

    def test_no_billion_dollar_depts(self, budget_pdf):
        """No individual department budget should exceed $1B."""
        df = self._run_parser(budget_pdf, 2026)
        over_1b = df[df["adopted_amount"] > 1_000_000_000]
        assert over_1b.empty, (
            f"Rows with adopted > $1B (likely tax roll values):\n{over_1b}"
        )


# ---------------------------------------------------------------------------
# Issue 2: Revenue scraper should not have impossible values or label bleed
# ---------------------------------------------------------------------------

class TestRevenueFiltering:
    """parse_all_funds_revenue should produce reasonable values and correct fund labels."""

    def _run_parser(self, budget_pdf, fy):
        pdf = budget_pdf(fy)
        pages = find_all_funds_revenue_pages(pdf)
        if not pages:
            return None
        return parse_all_funds_revenue(pdf, pages, fy)

    def test_no_billion_dollar_line_items(self, budget_pdf):
        """Non-total revenue items should not exceed $500M."""
        for fy in [2024, 2026]:
            df = self._run_parser(budget_pdf, fy)
            if df is None or df.empty:
                continue
            non_total = df[~df["line_item"].str.upper().str.startswith("TOTAL")]
            over_500m = non_total[non_total["adopted_amount"] > 500_000_000]
            assert over_500m.empty, (
                f"FY{fy} has non-total items > $500M:\n{over_500m}"
            )

    def test_fund_labels_no_bleed(self, budget_pdf):
        """Fund label should not be set from TOTAL line text."""
        for fy in [2024, 2026]:
            df = self._run_parser(budget_pdf, fy)
            if df is None or df.empty:
                continue
            unique_funds = set(df["fund"].unique())
            unexpected = unique_funds - CANONICAL_FUND_LABELS
            for f in unexpected:
                assert len(f) > 3, f"FY{fy} has suspicious fund label: '{f}'"

    def test_revenue_rows_preserve_fund_provenance(self, budget_pdf):
        df = self._run_parser(budget_pdf, 2026)
        if df is None or df.empty:
            return

        assert {"fund_raw", "is_total_row"}.issubset(df.columns)
        assert df["fund"].isin(CANONICAL_FUND_LABELS).all()
        total_rows = df[df["is_total_row"]]
        assert not total_rows.empty
        assert total_rows["line_item"].str.upper().str.startswith("TOTAL").all()


class TestRevenueNormalizationHelpers:
    def test_normalize_fund_label_aliases(self):
        assert normalize_fund_label("GENERAL FUND") == "General Fund"
        assert normalize_fund_label("Special Revenue Funds") == "Special Revenue Funds"
        assert normalize_fund_label("TRUST FUND") == "Trust Funds"
        assert normalize_fund_label("INTERNAL SERVICE FUNDS") == "Internal Service Funds"
        assert normalize_fund_label("OTHER FUNDS") == "Other Funds"
        assert normalize_fund_label("TOTAL GENERAL FUND") is None
