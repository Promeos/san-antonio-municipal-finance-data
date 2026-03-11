"""
Scrape budget-vs-actual tables from City of San Antonio ACFR PDFs.

Extracts the RSI Budgetary Comparison Schedule (General Fund) from each ACFR.
This table shows Original Budget, Final Budget, Actual amounts, and Variance.
All values in the PDFs are expressed in thousands.

Usable range: FY 2010–2024 (older PDFs are scanned images, not text-extractable).
"""

import re
import pdfplumber
import pandas as pd
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PDF_DIR = DATA_DIR / "acfr_pdfs"
OUTPUT_DIR = DATA_DIR / "processed"


def extract_dollar_amount(s: str) -> float | None:
    """Parse a dollar amount string like '1,695' or '(2,361)' into a float."""
    if not s or s.strip() in ("", "-", "—", "‐", "N/A"):
        return None
    s = s.strip().replace("$", "").replace(" ", "").replace("\t", "")
    # Handle dash variants meaning zero
    if s in ("-", "—", "‐"):
        return 0.0
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]
    s = s.replace(",", "")
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


# Canonical labels to normalize inconsistent spacing/naming across years
REVENUE_LABELS = {
    "taxes": "Taxes",
    "licensesandpermits": "Licenses and Permits",
    "licenses and permits": "Licenses and Permits",
    "intergovernmental": "Intergovernmental",
    "revenuesfromutilities": "Revenues from Utilities",
    "revenues from utilities": "Revenues from Utilities",
    "chargesforservices": "Charges for Services",
    "charges for services": "Charges for Services",
    "finesandforfeits": "Fines and Forfeits",
    "fines and forfeits": "Fines and Forfeits",
    "miscellaneous": "Miscellaneous",
    "investmentearnings": "Investment Earnings",
    "investment earnings": "Investment Earnings",
    "transfersfromotherfunds": "Transfers from Other Funds",
    "transfers from other funds": "Transfers from Other Funds",
    "contributions": "Contributions",
    "amountsavailableforappropriation": "Amounts Available for Appropriation",
    "amounts available for appropriation": "Amounts Available for Appropriation",
}

EXPENDITURE_LABELS = {
    "generalgovernment": "General Government",
    "general government": "General Government",
    "publicsafety": "Public Safety",
    "public safety": "Public Safety",
    "publicworks": "Public Works",
    "public works": "Public Works",
    "healthservices": "Health Services",
    "health services": "Health Services",
    "sanitation": "Sanitation",
    "cultureandrecreation": "Culture and Recreation",
    "culture and recreation": "Culture and Recreation",
    "welfare": "Welfare",
    "economicdevelopmentandopportunity": "Economic Development and Opportunity",
    "economic development and opportunity": "Economic Development and Opportunity",
    "urbanredevelopmentandhousing": "Urban Redevelopment and Housing",
    "urban redevelopment and housing": "Urban Redevelopment and Housing",
    "environmental": "Environmental",
    "conventionandtourism": "Convention and Tourism",
    "convention and tourism": "Convention and Tourism",
    "transferstootherfunds": "Transfers to Other Funds",
    "transfers to other funds": "Transfers to Other Funds",
    "totalchargestoappropriations:": "Total Charges to Appropriations",
    "total charges to appropriations:": "Total Charges to Appropriations",
    "totalchargestoappropriations": "Total Charges to Appropriations",
    "total charges to appropriations": "Total Charges to Appropriations",
    # Debt service sub-items (FY2015 has these)
    "principalretirement": "Principal Retirement",
    "principal retirement": "Principal Retirement",
    "interest": "Interest",
}


def normalize_label(raw: str, section: str) -> str | None:
    """Normalize a raw label to a canonical name, or return None if unrecognized."""
    cleaned = raw.strip().rstrip(":").strip()
    # Remove leading $ signs
    cleaned = re.sub(r"^\$\s*", "", cleaned)
    key = cleaned.lower().replace("‐", "").replace("-", "").replace("–", "")

    lookup = REVENUE_LABELS if section == "revenue" else EXPENDITURE_LABELS
    if key in lookup:
        return lookup[key]

    # Fuzzy: strip all spaces and try again
    key_nospace = key.replace(" ", "")
    for k, v in lookup.items():
        if k.replace(" ", "") == key_nospace:
            return v

    return None


def clean_text(text: str) -> str:
    """Remove (cid:N) characters and normalize spaces in extracted PDF text."""
    text = re.sub(r"\(cid:\d+\)", " ", text)
    # Collapse multiple spaces but preserve newlines
    text = re.sub(r"[^\S\n]+", " ", text)
    return text


def find_budgetary_comparison_page(pdf) -> int | None:
    """Find the RSI Budgetary Comparison Schedule page for the General Fund."""
    for i in range(len(pdf.pages)):
        text = clean_text((pdf.pages[i].extract_text() or "")).upper()
        # Some PDFs have spaces within words like "B UDGETARY"
        text_nospace = text.replace(" ", "")
        if "BUDGETARYCOMPARISON" in text_nospace and "GENERALFUND" in text_nospace:
            # Confirm it has the column headers
            if ("ORIGINAL" in text or "BUDGETED" in text_nospace) and "ACTUAL" in text:
                return i
    return None


def collapse_spaced_numbers(line: str) -> str:
    """Fix numbers with internal spaces like '6 5,358' -> '65,358' or '8 ,680' -> '8,680'.

    Some ACFR PDFs (FY2011, 2018, 2021, 2022) insert spaces within digit groups.
    Only collapses when a lone digit (not preceded by another digit or comma)
    is followed by a space and then more digits — safe for lines where
    separate column values are space-separated.
    """
    # Pattern 1: '6 5,358' — digit, space, digit (not preceded by digit/comma)
    line = re.sub(r"(?<![,\d])(\d) (?=\d[\d,])", r"\1", line)
    # Pattern 2: '8 ,680' — digit, space, comma-digits (space before comma in number)
    line = re.sub(r"(\d) (?=,\d{3})", r"\1", line)
    return line


def parse_budgetary_comparison(pdf, page_idx: int, fy: int) -> list[dict]:
    """Parse the RSI Budgetary Comparison Schedule from a single page."""
    raw = pdf.pages[page_idx].extract_text(layout=True) or ""
    # Clean cid characters from some PDFs
    raw = re.sub(r"\(cid:\d+\)", "", raw)

    lines = raw.split("\n")
    rows = []
    section = None  # "revenue" or "expenditure"

    for line in lines:
        line = collapse_spaced_numbers(line)
        upper = line.upper().strip()

        # Section detection
        if "RESOURCES (INFLOWS)" in upper or "RESOURCES(INFLOWS)" in upper:
            section = "revenue"
            continue
        if "CHARGES TO APPROPRIATIONS" in upper and "OUTFLOWS" in upper:
            section = "expenditure"
            # Don't continue — this line might also be "Total Charges to Appropriations"
            if "TOTAL" not in upper:
                continue

        if section is None:
            continue

        # Stop at the GAAP reconciliation section
        if "EXPLANATION OF DIFFERENCES" in upper:
            break
        if "SURPLUS" in upper and "DEFICIENCY" in upper:
            break
        if "FUND BALANCE ALLOCATION" in upper or "FUNDBALANCEALLOCATION" in upper:
            break
        if "EXCESS" in upper and "DEFICIENCY" in upper:
            break

        # Extract dollar amounts (including negative in parens)
        nums = re.findall(r"\(?\$?\s*[\d,]{1,}\)?", line)
        # Filter to actual numbers (at least 1 digit)
        nums = [n for n in nums if re.search(r"\d", n)]
        if not nums:
            continue

        # Get the label: everything before the first number
        first_num_match = re.search(r"\(?\$?\s*[\d,]{2,}", line)
        if not first_num_match:
            continue
        label_raw = line[:first_num_match.start()].strip()

        # Normalize label
        label = normalize_label(label_raw, section)
        if label is None:
            # Try with the "Total" prefix for expenditure totals
            if section == "expenditure" and "TOTAL" in upper:
                label = "Total Charges to Appropriations"
            else:
                continue

        # Parse all 4 amounts: Original, Final, Actual, Variance
        amounts = [extract_dollar_amount(n) for n in nums]
        amounts = [a for a in amounts if a is not None]

        if len(amounts) < 3:
            continue

        row = {
            "fiscal_year": fy,
            "section": section,
            "line_item": label,
            "original_budget": amounts[0] * 1000,  # Convert from thousands
            "final_budget": amounts[1] * 1000,
            "actual": amounts[2] * 1000,
        }
        if len(amounts) >= 4:
            row["variance"] = amounts[3] * 1000
        else:
            row["variance"] = row["actual"] - row["final_budget"]

        rows.append(row)

    return rows


def scrape_acfr_pdf(pdf_path: Path) -> pd.DataFrame:
    """Scrape the budgetary comparison schedule from a single ACFR PDF."""
    match = re.search(r"fy(\d{4})", pdf_path.stem)
    if not match:
        raise ValueError(f"Cannot determine FY from filename: {pdf_path.name}")
    fy = int(match.group(1))

    print(f"  Scraping FY {fy} ({pdf_path.name})...")
    pdf = pdfplumber.open(pdf_path)

    try:
        page_idx = find_budgetary_comparison_page(pdf)
        if page_idx is None:
            print(f"    [SKIP] No budgetary comparison page found")
            return pd.DataFrame()

        rows = parse_budgetary_comparison(pdf, page_idx, fy)
        if not rows:
            print(f"    [SKIP] Could not parse budgetary comparison table")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        print(f"    Found {len(df)} line items (page {page_idx})")
        return df

    finally:
        pdf.close()


def scrape_all_acfrs():
    """Scrape all downloaded ACFR PDFs and save combined dataset."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(PDF_DIR.glob("fy*-acfr.pdf"))
    if not pdf_files:
        print(f"No ACFR PDFs found in {PDF_DIR}. Run download_acfrs.py first.")
        return

    print(f"Found {len(pdf_files)} ACFR PDFs\n")

    all_rows = []

    for pdf_path in pdf_files:
        try:
            df = scrape_acfr_pdf(pdf_path)
            if not df.empty:
                all_rows.append(df)
        except Exception as e:
            print(f"  ERROR scraping {pdf_path.name}: {e}")

    if all_rows:
        combined = pd.concat(all_rows, ignore_index=True)
        output_path = OUTPUT_DIR / "acfr_budget_vs_actual.csv"
        combined.to_csv(output_path, index=False)
        print(f"\nSaved {output_path.name} ({len(combined)} rows)")
        print(f"Fiscal years: {sorted(combined['fiscal_year'].unique())}")

        # Summary stats
        rev = combined[combined["line_item"] == "Amounts Available for Appropriation"]
        if not rev.empty:
            print(f"\nGeneral Fund Revenue (Actual, in billions):")
            for _, r in rev.sort_values("fiscal_year").iterrows():
                print(f"  FY {r['fiscal_year']}: ${r['actual']/1e9:.2f}B")
    else:
        print("\nNo data extracted from any ACFR.")

    print("\nDone!")


if __name__ == "__main__":
    scrape_all_acfrs()
