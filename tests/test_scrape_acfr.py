"""Tests for ACFR PDF scrapers — budget vs actual."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrape_acfr import (
    find_budgetary_comparison_page,
    parse_budgetary_comparison,
)


# ---------------------------------------------------------------------------
# Issue 6: ACFR FY2012-2014 should have expenditure rows
# ---------------------------------------------------------------------------

class TestACFRExpenditures:
    """parse_budgetary_comparison should extract both revenue and expenditure rows."""

    def _run_parser(self, acfr_pdf, fy):
        pdf = acfr_pdf(fy)
        page_idx = find_budgetary_comparison_page(pdf)
        if page_idx is None:
            return None
        return parse_budgetary_comparison(pdf, page_idx, fy)

    def test_fy2012_has_expenditures(self, acfr_pdf):
        rows = self._run_parser(acfr_pdf, 2012)
        assert rows is not None, "FY2012 parser returned None"
        exp_rows = [r for r in rows if r["section"] == "expenditure"]
        assert len(exp_rows) > 0, "FY2012 has 0 expenditure rows"

    def test_fy2013_has_expenditures(self, acfr_pdf):
        rows = self._run_parser(acfr_pdf, 2013)
        assert rows is not None, "FY2013 parser returned None"
        exp_rows = [r for r in rows if r["section"] == "expenditure"]
        assert len(exp_rows) > 0, "FY2013 has 0 expenditure rows"

    def test_fy2014_has_expenditures(self, acfr_pdf):
        rows = self._run_parser(acfr_pdf, 2014)
        assert rows is not None, "FY2014 parser returned None"
        exp_rows = [r for r in rows if r["section"] == "expenditure"]
        assert len(exp_rows) > 0, "FY2014 has 0 expenditure rows"

    def test_fy2015_unchanged(self, acfr_pdf):
        """FY2015 should still work correctly (regression check)."""
        rows = self._run_parser(acfr_pdf, 2015)
        assert rows is not None, "FY2015 parser returned None"
        rev_rows = [r for r in rows if r["section"] == "revenue"]
        exp_rows = [r for r in rows if r["section"] == "expenditure"]
        assert len(rev_rows) >= 10, f"FY2015 has only {len(rev_rows)} revenue rows"
        assert len(exp_rows) >= 10, f"FY2015 has only {len(exp_rows)} expenditure rows"
