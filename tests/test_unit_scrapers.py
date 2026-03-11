import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.scrape_budgets import CANONICAL_FUND_LABELS, extract_dollar_amount, normalize_fund_label


def test_normalize_fund_label_aliases():
    assert normalize_fund_label("GENERAL FUND") == "General Fund"
    assert normalize_fund_label("Special Revenue Funds") == "Special Revenue Funds"
    assert normalize_fund_label("TRUST FUND") == "Trust Funds"
    assert normalize_fund_label("INTERNAL SERVICE FUNDS") == "Internal Service Funds"
    assert normalize_fund_label("OTHER FUNDS") == "Other Funds"
    assert normalize_fund_label("TOTAL GENERAL FUND") is None


def test_canonical_fund_labels_are_stable():
    assert CANONICAL_FUND_LABELS == {
        "Enterprise Funds",
        "General Fund",
        "Internal Service Funds",
        "Other Funds",
        "Special Revenue Funds",
        "Trust Funds",
    }


def test_extract_dollar_amount_handles_parentheses():
    assert extract_dollar_amount("1,234,567") == 1234567.0
    assert extract_dollar_amount("(2,500)") == -2500.0
    assert extract_dollar_amount("-") is None
