"""
Scrape Capital Improvement Program (CIP) tables from City of San Antonio budget PDFs.

Extracts three table types:
1. CIP by Program Category — annual and multi-year spending by category (Streets, Parks, etc.)
2. CIP by Revenue Source — how capital spending is funded (G.O. Bonds, Certificates of Obligation, etc.)
3. Bond Program Status — voter-approved bond authorizations vs. debt issued vs. unissued

Uses pdfplumber to find and parse tables dynamically across FY2008–FY2026 PDFs.
"""

import re
import pdfplumber
import pandas as pd
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PDF_DIR = DATA_DIR / "pdfs"
OUTPUT_DIR = DATA_DIR / "processed"


def extract_dollar_amount(s: str) -> float | None:
    """Parse a dollar/number string like '$237,958' or '591,536' into a float."""
    if not s or s.strip() in ("", "-", "N/A"):
        return None
    s = s.strip().replace("$", "").replace(" ", "").replace("\t", "")
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


def find_cip_category_pages(pdf) -> list[int]:
    """Find pages with the CIP by Program Category summary table.

    Looks for two variants:
    - Budget Summary section table (e.g. "FY 2025 – FY 2030 Capital Program by Category")
    - CIP section detailed table (e.g. "Capital Improvements Program Costs by Program Category")
    """
    results = []
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lower = text.lower()
        # Must mention capital improvement/program and category, plus have a total line
        if ("capital" in lower
                and ("improvement" in lower or "program" in lower)
                and "category" in lower
                and "total" in lower):
            tables = page.extract_tables()
            if tables:
                # Verify at least one table has program-like rows
                for t in tables:
                    flat = " ".join(str(c) for row in t for c in row if c).lower()
                    if "streets" in flat or "parks" in flat or "drainage" in flat:
                        results.append(i)
                        break
    return results


def find_cip_revenue_pages(pdf) -> list[int]:
    """Find pages with CIP by Revenue Source table."""
    results = []
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lower = text.lower()
        if ("revenue source" in lower
                and ("capital" in lower or "cip" in lower)
                and "total" in lower):
            tables = page.extract_tables()
            if tables:
                for t in tables:
                    flat = " ".join(str(c) for row in t for c in row if c).lower()
                    if "bond" in flat or "certificate" in flat or "tax notes" in flat:
                        results.append(i)
                        break
    return results


def find_bond_status_pages(pdf) -> list[int]:
    """Find pages with bond program authorization/issuance status tables."""
    results = []
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        lower = text.lower()
        if ("bond program" in lower
                and ("authorized" in lower or "unissued" in lower)
                and "total" in lower):
            tables = page.extract_tables()
            if tables:
                results.append(i)
    return results


def clean_label(s: str) -> str:
    """Clean a table cell label."""
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'^[\$\s]+', '', s)
    return s.strip()


def parse_cip_categories(pdf, pages: list[int], fy: int) -> pd.DataFrame:
    """Parse CIP by Program Category tables.

    These tables have columns like:
        Program Category | FY 20XX Amount | FY 20XX - FY 20YY Amount | %

    Or the detailed multi-year version:
        Program | FY2025 | FY2026 | ... | FY2030 | Total | %

    We extract the current-FY amount and the multi-year total for each category.
    """
    # Collect candidates from all pages, then pick the best set
    page_results = []

    for page_idx in pages:
        page = pdf.pages[page_idx]
        tables = page.extract_tables()
        page_rows = []

        for table in tables:
            if not table or len(table) < 1:
                continue

            for row in table:
                cells = [c for c in row if c is not None]
                if not cells:
                    continue

                # Get the label (first non-empty cell that looks like text)
                label = None
                amounts = []
                for cell in cells:
                    cell_str = str(cell).strip()
                    # Skip percentage cells
                    if cell_str.endswith('%'):
                        continue
                    # Skip page number references (3-digit numbers alone)
                    if re.match(r'^\d{1,3}$', cell_str) and not cell_str.startswith('$'):
                        continue
                    val = extract_dollar_amount(cell_str)
                    if val is not None:
                        amounts.append(val)
                    elif label is None and len(cell_str) >= 3 and not re.match(r'^[\d\$,.\s]+$', cell_str):
                        label = clean_label(cell_str)

                if not label or not amounts:
                    continue

                # Skip header rows and sub-headers
                label_lower = label.lower()
                if any(skip in label_lower for skip in [
                    'program category', 'amount', 'number', 'page',
                    'figure', 'in thousands', 'includes',
                ]):
                    continue

                is_total = label_lower.startswith('total')

                # Determine current-FY and multi-year amounts
                if len(amounts) >= 2:
                    fy_amount = amounts[0]
                    multiyear_amount = amounts[-1]
                elif len(amounts) == 1:
                    fy_amount = amounts[0]
                    multiyear_amount = None
                else:
                    continue

                if is_total:
                    label = "Total"

                page_rows.append({
                    "category": label,
                    "fy_amount": fy_amount * 1000,  # Tables are in thousands
                    "multiyear_amount": multiyear_amount * 1000 if multiyear_amount else None,
                    "fiscal_year": fy,
                })

        if page_rows:
            page_results.append(page_rows)

    if not page_results:
        return pd.DataFrame()

    # Pick the page with the most non-Total rows (best extraction)
    best = max(page_results, key=lambda pr: sum(1 for r in pr if r["category"] != "Total"))

    # Deduplicate within the best page set
    seen = set()
    rows = []
    for r in best:
        key = r["category"].lower()
        if key in seen:
            continue
        seen.add(key)
        rows.append(r)

    return pd.DataFrame(rows)


def parse_cip_revenue_sources(pdf, pages: list[int], fy: int) -> pd.DataFrame:
    """Parse CIP by Revenue Source tables.

    Columns: Revenue Source | FY 20XX Amount | Multi-year Amount | %
    """
    # Known revenue source keywords to validate rows
    valid_source_keywords = [
        'bond', 'certificate', 'tax note', 'airport', 'aviation', 'grant',
        'previous debt', 'other', 'storm water', 'self-supporting', 'total',
    ]

    page_results = []

    for page_idx in pages:
        page = pdf.pages[page_idx]
        tables = page.extract_tables()
        page_rows = []

        for table in tables:
            if not table or len(table) < 2:
                continue

            for row in table:
                cells = [c for c in row if c is not None]
                if not cells:
                    continue

                label = None
                amounts = []
                for cell in cells:
                    cell_str = str(cell).strip()
                    if cell_str.endswith('%'):
                        continue
                    val = extract_dollar_amount(cell_str)
                    if val is not None:
                        amounts.append(val)
                    elif label is None and len(cell_str) >= 3 and not re.match(r'^[\d\$,.\s]+$', cell_str):
                        label = clean_label(cell_str.split('\n')[0])

                if not label or not amounts:
                    continue

                label_lower = label.lower()
                if any(skip in label_lower for skip in [
                    'revenue source', 'amount', 'figure', 'in thousands',
                ]):
                    continue

                # Validate this looks like a revenue source
                if not any(kw in label_lower for kw in valid_source_keywords):
                    continue

                is_total = label_lower.startswith('total')

                if len(amounts) >= 2:
                    fy_amount = amounts[0]
                    multiyear_amount = amounts[-1]
                elif len(amounts) == 1:
                    fy_amount = amounts[0]
                    multiyear_amount = None
                else:
                    continue

                if is_total:
                    label = "Total"

                page_rows.append({
                    "source": label,
                    "fy_amount": fy_amount * 1000,
                    "multiyear_amount": multiyear_amount * 1000 if multiyear_amount else None,
                    "fiscal_year": fy,
                })

        if page_rows:
            page_results.append(page_rows)

    if not page_results:
        return pd.DataFrame()

    # Pick the page with the most non-Total rows
    best = max(page_results, key=lambda pr: sum(1 for r in pr if r["source"] != "Total"))

    seen = set()
    rows = []
    for r in best:
        key = r["source"].lower()
        if key in seen:
            continue
        seen.add(key)
        rows.append(r)

    return pd.DataFrame(rows)


def parse_bond_status(pdf, pages: list[int], fy: int) -> pd.DataFrame:
    """Parse bond program authorization/issuance status tables.

    Typical columns: Proposition | Amount Authorized | Debt Issued | Unissued Debt
    Values are in millions.
    """
    rows = []

    for page_idx in pages:
        page = pdf.pages[page_idx]
        text = page.extract_text() or ""

        # Determine which bond program this is (2022, 2017, 2012, 2007)
        bond_year = None
        for year in [2022, 2017, 2012, 2007, 2003]:
            if str(year) in text and "bond program" in text.lower():
                bond_year = year
                break

        tables = page.extract_tables()
        for table in tables:
            if not table or len(table) < 3:
                continue

            # Check if this looks like a bond status table
            flat = " ".join(str(c) for row in table for c in row if c).lower()
            if "authorized" not in flat and "unissued" not in flat:
                continue

            for row in table:
                cells = [c for c in row if c is not None]
                if not cells:
                    continue

                label = None
                amounts = []
                for cell in cells:
                    cell_str = str(cell).strip()
                    val = extract_dollar_amount(cell_str)
                    if val is not None:
                        amounts.append(val)
                    elif label is None and len(cell_str) >= 3 and not re.match(r'^[\d\$,.\s]+$', cell_str):
                        label = clean_label(cell_str)

                if not label or not amounts:
                    continue

                label_lower = label.lower()
                if any(skip in label_lower for skip in [
                    'amount', 'improvements', 'debt issued', 'in millions',
                    'represents', 'table',
                ]):
                    continue

                is_total = label_lower.startswith('total')
                if is_total:
                    label = "Total"

                # amounts are in millions
                authorized = amounts[0] * 1_000_000 if len(amounts) >= 1 else None
                issued = amounts[1] * 1_000_000 if len(amounts) >= 2 else None
                unissued = amounts[2] * 1_000_000 if len(amounts) >= 3 else None

                rows.append({
                    "bond_program": f"{bond_year} G.O. Bonds" if bond_year else "Unknown",
                    "proposition": label,
                    "authorized": authorized,
                    "issued": issued,
                    "unissued": unissued,
                    "fiscal_year": fy,
                })

    return pd.DataFrame(rows)


def scrape_cip_from_pdf(pdf_path: Path) -> dict[str, pd.DataFrame]:
    """Scrape all CIP tables from a single budget PDF."""
    match = re.search(r'fy(\d{4})', pdf_path.stem)
    if not match:
        raise ValueError(f"Cannot determine FY from filename: {pdf_path.name}")
    fy = int(match.group(1))

    print(f"  Scraping FY {fy} ({pdf_path.name})...")
    pdf = pdfplumber.open(pdf_path)

    results = {}
    try:
        # CIP by Program Category
        pages = find_cip_category_pages(pdf)
        if pages:
            df = parse_cip_categories(pdf, pages, fy)
            if not df.empty:
                results["cip_categories"] = df
                print(f"    CIP Categories: {len(df)} rows from {len(pages)} pages")
        else:
            print(f"    CIP Categories: no pages found")

        # CIP by Revenue Source
        pages = find_cip_revenue_pages(pdf)
        if pages:
            df = parse_cip_revenue_sources(pdf, pages, fy)
            if not df.empty:
                results["cip_revenue"] = df
                print(f"    CIP Revenue Sources: {len(df)} rows from {len(pages)} pages")
        else:
            print(f"    CIP Revenue Sources: no pages found")

        # Bond Program Status
        pages = find_bond_status_pages(pdf)
        if pages:
            df = parse_bond_status(pdf, pages, fy)
            if not df.empty:
                results["bond_status"] = df
                print(f"    Bond Status: {len(df)} rows from {len(pages)} pages")
        else:
            print(f"    Bond Status: no pages found")

    finally:
        pdf.close()

    return results


def scrape_all_cip():
    """Scrape CIP tables from all budget PDFs and save combined datasets."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(PDF_DIR.glob("fy*-adopted-budget.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {PDF_DIR}. Run download_budgets.py first.")
        return

    print(f"Found {len(pdf_files)} budget PDFs\n")

    all_categories = []
    all_revenue = []
    all_bonds = []

    for pdf_path in pdf_files:
        try:
            results = scrape_cip_from_pdf(pdf_path)
            if "cip_categories" in results:
                all_categories.append(results["cip_categories"])
            if "cip_revenue" in results:
                all_revenue.append(results["cip_revenue"])
            if "bond_status" in results:
                all_bonds.append(results["bond_status"])
        except Exception as e:
            print(f"  ERROR scraping {pdf_path.name}: {e}")

    # Save combined datasets
    if all_categories:
        df = pd.concat(all_categories, ignore_index=True)
        df.to_csv(OUTPUT_DIR / "cip_categories.csv", index=False)
        print(f"\nSaved cip_categories.csv ({len(df)} rows, "
              f"FY{df['fiscal_year'].min()}–{df['fiscal_year'].max()})")

    if all_revenue:
        df = pd.concat(all_revenue, ignore_index=True)
        df.to_csv(OUTPUT_DIR / "cip_revenue_sources.csv", index=False)
        print(f"Saved cip_revenue_sources.csv ({len(df)} rows, "
              f"FY{df['fiscal_year'].min()}–{df['fiscal_year'].max()})")

    if all_bonds:
        df = pd.concat(all_bonds, ignore_index=True)
        df.to_csv(OUTPUT_DIR / "bond_status.csv", index=False)
        print(f"Saved bond_status.csv ({len(df)} rows, "
              f"FY{df['fiscal_year'].min()}–{df['fiscal_year'].max()})")

    print("\nDone!")


if __name__ == "__main__":
    scrape_all_cip()
