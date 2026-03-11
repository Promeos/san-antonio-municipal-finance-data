"""Shared fixtures for scraper tests."""

import pdfplumber
import pandas as pd
import pytest
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PDF_DIR = DATA_DIR / "pdfs"
ACFR_DIR = DATA_DIR / "acfr_pdfs"
GOLDEN_DIR = Path(__file__).resolve().parent / "golden"


@pytest.fixture
def budget_pdf():
    """Return an open pdfplumber handle for a given FY budget PDF."""
    handles = {}

    def _open(fy: int):
        if fy not in handles:
            path = PDF_DIR / f"fy{fy}-adopted-budget.pdf"
            if not path.exists():
                pytest.skip(f"PDF not found: {path}")
            handles[fy] = pdfplumber.open(path)
        return handles[fy]

    yield _open

    for h in handles.values():
        h.close()


@pytest.fixture
def acfr_pdf():
    """Return an open pdfplumber handle for a given FY ACFR PDF."""
    handles = {}

    def _open(fy: int):
        if fy not in handles:
            path = ACFR_DIR / f"fy{fy}-acfr.pdf"
            if not path.exists():
                pytest.skip(f"PDF not found: {path}")
            handles[fy] = pdfplumber.open(path)
        return handles[fy]

    yield _open

    for h in handles.values():
        h.close()


def load_golden(name: str) -> pd.DataFrame:
    """Load a golden CSV snapshot."""
    path = GOLDEN_DIR / f"{name}.csv"
    if not path.exists():
        pytest.skip(f"Golden file not found: {path}")
    return pd.read_csv(path)
