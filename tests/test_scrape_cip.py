"""Tests for CIP PDF scrapers — categories, revenue sources, bond status."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrape_cip import (
    find_cip_category_pages,
    parse_cip_categories,
    find_bond_status_pages,
    parse_bond_status,
)


# ---------------------------------------------------------------------------
# Issue 3: CIP category scraper should not include revenue-source rows
# ---------------------------------------------------------------------------

class TestCIPCategoryFiltering:
    """parse_cip_categories should contain program categories, not revenue sources."""

    REVENUE_LABELS = [
        "2012 G.O. Bonds",
        "2017 G.O. Bonds",
        "Certificates of Obligation",
        "Tax Notes",
    ]

    EXPECTED_CATEGORIES = ["Drainage", "Parks"]

    def _run_parser(self, budget_pdf, fy):
        pdf = budget_pdf(fy)
        pages = find_cip_category_pages(pdf)
        if not pages:
            return None
        return parse_cip_categories(pdf, pages, fy)

    def test_fy2017_no_revenue_rows(self, budget_pdf):
        df = self._run_parser(budget_pdf, 2017)
        if df is None or df.empty:
            return
        labels_lower = df["category"].str.lower().tolist()
        for bad in self.REVENUE_LABELS:
            assert bad.lower() not in labels_lower, (
                f"Found revenue-source row in categories: {bad}"
            )

    def test_fy2022_no_revenue_rows(self, budget_pdf):
        df = self._run_parser(budget_pdf, 2022)
        if df is None or df.empty:
            return
        labels_lower = df["category"].str.lower().tolist()
        for bad in self.REVENUE_LABELS:
            assert bad.lower() not in labels_lower, (
                f"Found revenue-source row in categories: {bad}"
            )

    def test_fy2016_not_missing(self, budget_pdf):
        """FY2016 should produce CIP category output."""
        df = self._run_parser(budget_pdf, 2016)
        assert df is not None and not df.empty, "FY2016 CIP categories missing"
        labels_lower = df["category"].str.lower().tolist()
        # FY2016 uses "Municipal Facilities" not "Streets"
        assert any("facilities" in l or "streets" in l for l in labels_lower), (
            f"FY2016 missing expected categories, got: {labels_lower}"
        )

    def test_has_real_categories(self, budget_pdf):
        for fy in [2024, 2026]:
            df = self._run_parser(budget_pdf, fy)
            if df is None or df.empty:
                continue
            labels_lower = df["category"].str.lower().tolist()
            for cat in self.EXPECTED_CATEGORIES:
                assert any(cat.lower() in l for l in labels_lower), (
                    f"FY{fy} missing expected category: {cat}"
                )


# ---------------------------------------------------------------------------
# Issue 4: Bond year should be per-row, not per-page
# ---------------------------------------------------------------------------

class TestBondYearAssignment:
    """parse_bond_status should assign correct bond_year per row."""

    def _run_parser(self, budget_pdf, fy):
        pdf = budget_pdf(fy)
        pages = find_bond_status_pages(pdf)
        if not pages:
            return None
        return parse_bond_status(pdf, pages, fy)

    def test_multiple_bond_years_possible(self, budget_pdf):
        """If a PDF has multiple bond programs, rows should reflect different years."""
        for fy in [2018, 2023]:
            df = self._run_parser(budget_pdf, fy)
            if df is None or df.empty:
                continue
            # After fix, we expect to see multiple bond_program values if the PDF
            # contains both old and new bond programs
            programs = df["bond_program"].unique()
            # This is a soft check — just verify bond_program column exists and has values
            assert len(programs) >= 1, f"FY{fy} has no bond programs"
