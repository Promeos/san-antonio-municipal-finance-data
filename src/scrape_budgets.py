"""
Scrape financial tables from City of San Antonio adopted budget PDFs.

Targets two key tables from each budget:
1. Combined Budget Summary — revenue and appropriations by category across all fund types
2. General Fund Department Summary — department-level adopted appropriations

Uses targeted page finding and text parsing to handle multi-column PDF layouts.
"""

import re
import pdfplumber
import pandas as pd
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PDF_DIR = DATA_DIR / "pdfs"
OUTPUT_DIR = DATA_DIR / "processed"


def extract_dollar_amount(s: str) -> float | None:
    """Parse a dollar amount string like '1,695,896,847' or '(2,361,151)' into a float."""
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


def find_combined_summary_pages(pdf) -> list[int]:
    """Find pages containing the Combined Budget Summary table."""
    results = []
    for i in range(len(pdf.pages)):
        text = (pdf.pages[i].extract_text() or "").upper()
        if "COMBINED BUDGET SUMMARY" in text and "ALL FUND" in text:
            results.append(i)
    return results


def find_all_funds_revenue_pages(pdf) -> list[int]:
    """Find pages with the All Funds Revenue Summary table (older format)."""
    results = []
    for i in range(len(pdf.pages)):
        text = (pdf.pages[i].extract_text() or "")
        upper = text.upper()
        # This specific table header appears in older budgets
        if "ALL FUNDS" in upper and "SUMMARY OF ADOPTED BUDGET REVENUES" in upper:
            results.append(i)
        elif "ALL FUNDS" in upper and "SUMMARY OF ADOPTED BUDGET" in upper and "REVENUE" in upper:
            results.append(i)
    return results


def find_general_fund_summary_pages(pdf) -> list[int]:
    """Find pages with the General Fund Summary of Adopted Budget.

    These pages have 'GENERAL FUND' and 'SUMMARY OF ADOPTED BUDGET' as
    a page header/title, and contain department appropriation lines.
    We specifically look for 'DEPARTMENTAL APPROPRIATIONS' to confirm.
    """
    results = []
    for i in range(len(pdf.pages)):
        text = (pdf.pages[i].extract_text() or "")
        upper = text.upper()
        lines = text.strip().split("\n")

        # The header should appear in the first few lines
        header_lines = "\n".join(lines[:6]).upper()
        if "GENERAL FUND" not in header_lines:
            continue
        if "SUMMARY OF ADOPTED BUDGET" not in header_lines:
            continue

        # Must have department data
        if "DEPARTMENTAL APPROPRIATIONS" in upper or "TOTAL APPROPRIATIONS" in upper:
            nums = re.findall(r'[\d,]{6,}', text)
            if len(nums) >= 5:
                results.append(i)
    return results


def parse_combined_summary(pdf, pages: list[int], fy: int) -> pd.DataFrame:
    """
    Parse the Combined Budget Summary pages.

    These pages have columns for fund types (General Fund, Special Revenue, etc.)
    We extract from the left page (General Fund column) and right page (Total All Funds).
    """
    rows = []
    section = "info"

    for page_idx in pages:
        text = pdf.pages[page_idx].extract_text() or ""
        lines = text.strip().split("\n")

        # Determine if this is the "right side" page (labels on right)
        is_right_page = any(
            "ENTERPRISE" in l.upper() or ("TOTAL" in l.upper() and "ALL FUNDS" in l.upper())
            for l in lines[:8]
        )

        for line in lines:
            upper = line.upper().strip()

            # Section tracking
            if "BEGINNING BALANCE" in upper:
                section = "balance"
            elif upper == "REVENUES":
                section = "revenue"
                continue
            elif upper == "APPROPRIATIONS":
                section = "appropriation"
                continue

            # Skip header/structural lines
            if any(skip in upper for skip in [
                "ADOPTED ANNUAL BUDGET", "COMBINED BUDGET SUMMARY",
                "FUND TYPES", "GOVERNMENTAL", "PROPRIETARY",
                "FIDUCIARY", "CITY OF SAN ANTONIO",
                "DOES NOT INCLUDE",
            ]):
                continue

            # Skip column header lines
            if re.match(r'^(SPECIAL|DEBT|GENERAL|INTERNAL|ENTERPRISE|TRUST|SERVICE|CAPITAL)\s', upper):
                continue

            # Extract data lines
            nums = re.findall(r'\(?\$?\s*[\d,]{3,}\)?', line)
            if not nums:
                continue

            # Get label text
            if is_right_page:
                parts = re.split(r'\(?\$?\s*[\d,]{3,}\)?', line)
                label = parts[-1].strip() if parts else ""
            else:
                parts = re.split(r'\(?\$?\s*[\d,]{3,}\)?', line)
                label = parts[0].strip() if parts else ""

            # Clean up label
            label = re.sub(r'^[\$\s]+', '', label).strip()
            label = re.sub(r'[\$\s]+$', '', label).strip()

            # Skip lines that are just zeros or don't have a real label
            if not label or len(label) < 3 or re.match(r'^[\d\s\$,\.]+$', label):
                continue

            # Parse amounts
            amounts = [extract_dollar_amount(n) for n in nums]
            amounts = [a for a in amounts if a is not None]
            if not amounts:
                continue

            fund = "Total All Funds" if is_right_page else "General Fund"
            # For right page use last amount (Total All Funds column)
            # For left page use first amount (General Fund column)
            amount = amounts[-1] if is_right_page else amounts[0]

            rows.append({
                "section": section,
                "line_item": label,
                "amount": amount,
                "fund": fund,
                "fiscal_year": fy,
            })

    return pd.DataFrame(rows)


def parse_all_funds_revenue(pdf, pages: list[int], fy: int) -> pd.DataFrame:
    """
    Parse the All Funds Revenue Summary (common in older budgets like FY2015).
    This is a single wide table with columns: Actual, Budget, Estimated, Current Svc, Changes, Adopted.
    Revenue line items are grouped by fund.
    """
    rows = []
    current_fund = "General Fund"

    for page_idx in pages:
        text = pdf.pages[page_idx].extract_text() or ""
        lines = text.strip().split("\n")

        for line in lines:
            upper = line.upper().strip()

            # Skip headers
            if any(skip in upper for skip in [
                "ALL FUNDS", "SUMMARY OF ADOPTED", "PROGRAM CHANGES",
                "ACTUAL", "BUDGET", "ESTIMATED", "CURRENT SVC",
                "CITY OF SAN ANTONIO", "ADOPTED FY",
            ]):
                continue

            # Track current fund
            if "General Fund" in line and not re.search(r'[\d,]{4,}', line):
                current_fund = "General Fund"
                continue
            elif "Special Revenue" in line and not re.search(r'[\d,]{4,}', line):
                current_fund = "Special Revenue Funds"
                continue
            elif "Enterprise Fund" in line and not re.search(r'[\d,]{4,}', line):
                current_fund = "Enterprise Funds"
                continue
            elif "Trust Fund" in line and not re.search(r'[\d,]{4,}', line):
                current_fund = "Trust Funds"
                continue
            elif "Internal Service" in line and not re.search(r'[\d,]{4,}', line):
                current_fund = "Internal Service Funds"
                continue

            # Extract data
            nums = re.findall(r'\(?\$?\s*[\d,]{4,}\)?', line)
            if not nums:
                continue

            label = re.split(r'\(?\$?\s*[\d,]{4,}\)?', line)[0].strip()
            label = re.sub(r'^[\$\s]+', '', label).strip()

            if not label or len(label) < 3:
                continue

            amounts = [extract_dollar_amount(n) for n in nums]
            amounts = [a for a in amounts if a is not None]

            if not amounts:
                continue

            # Last column is the Adopted amount
            adopted = amounts[-1]

            # Check for fund totals
            if label.upper().startswith("TOTAL"):
                fund_name = label.replace("TOTAL", "").replace("Total", "").strip()
                if fund_name:
                    current_fund = fund_name

            rows.append({
                "fund": current_fund,
                "line_item": label,
                "adopted_amount": adopted,
                "fiscal_year": fy,
            })

    return pd.DataFrame(rows)


def parse_general_fund_depts(pdf, pages: list[int], fy: int) -> pd.DataFrame:
    """
    Parse General Fund department appropriations.

    The table spans 2 pages (left side has prior year columns + reductions/mandates,
    right side has improvements + adopted totals). Department names appear on both pages.

    We look for the page with the final "ADOPTED" column.
    """
    rows = []
    seen_depts = set()

    # Known department names to help identify valid lines
    known_dept_keywords = [
        "animal care", "police", "fire", "parks", "library", "health",
        "public works", "human", "code enforcement", "finance", "city manager",
        "city attorney", "city auditor", "city clerk", "economic development",
        "municipal court", "solid waste", "airport", "development services",
        "transportation", "neighborhood", "communications", "innovation",
        "planning", "historic", "homeless", "mayor", "military",
        "non-departmental", "agencies", "transfers", "world heritage",
        "arts", "convention", "311", "customer service", "arrestee",
        "center city", "compliance", "government affairs", "management & budget",
        "municipal election", "pre-k", "ready to work", "resiliency",
        "information technology", "self-insurance", "storm water",
        "total appropriations", "total available", "gross ending",
    ]

    for page_idx in pages:
        text = pdf.pages[page_idx].extract_text() or ""
        lines = text.strip().split("\n")

        # Check if this page has the ADOPTED column header
        has_adopted_header = any("ADOPTED" in l.upper() for l in lines[:5])
        if not has_adopted_header:
            # Check if the last column appears to be adopted amounts
            # by looking for "TOTAL APPROPRIATIONS" with amounts
            has_total = any("TOTAL APPROPRIATIONS" in l.upper() for l in lines)
            if not has_total:
                continue

        for line in lines:
            upper = line.upper().strip()

            # Skip headers
            if any(skip in upper for skip in [
                "GENERAL FUND", "SUMMARY OF ADOPTED",
                "DEPARTMENTAL APPROPRIATIONS",
                "FY 20", "BUDGET", "ESTIMATED", "CURRENT",
                "PROGRAM CHANGES", "IMPROVEMENTS", "MANDATES",
                "REDUCTIONS", "EMPLOYEE", "COMPENSATION",
                "REORGAN", "CITY OF SAN ANTONIO",
                "BUDGET RESERVES", "ANNUAL BUDGETED",
                "% OF GENERAL", "LESS: BUDGETED",
            ]):
                continue

            # Extract lines with dollar amounts
            nums = re.findall(r'\(?\$?\s*[\d,]{4,}\)?', line)
            if not nums:
                continue

            # Get label from left or right side
            parts = re.split(r'\(?\$?\s*[\d,]{4,}\)?', line)
            label = parts[0].strip()
            if not label or len(label) < 3:
                # Try right side (some pages have labels on the right)
                label = parts[-1].strip() if parts else ""

            label = re.sub(r'^[\$\s]+', '', label).strip()
            label = re.sub(r'[\$\s]+$', '', label).strip()

            if not label or len(label) < 3:
                continue

            # Parse amounts - the last one is typically the Adopted figure
            amounts = [extract_dollar_amount(n) for n in nums]
            amounts = [a for a in amounts if a is not None]

            if not amounts:
                continue

            adopted = amounts[-1]

            # Deduplicate: same department may appear on both pages of the spread
            dept_key = label.lower().strip()
            if dept_key in seen_depts:
                # Update with the value from the page that has the Adopted column
                for i, row in enumerate(rows):
                    if row["department"].lower().strip() == dept_key:
                        if has_adopted_header:
                            rows[i]["adopted_amount"] = adopted
                        break
                continue

            seen_depts.add(dept_key)
            rows.append({
                "department": label,
                "adopted_amount": adopted,
                "fiscal_year": fy,
            })

    return pd.DataFrame(rows)


def scrape_budget_pdf(pdf_path: Path) -> dict[str, pd.DataFrame]:
    """Scrape all key tables from a single budget PDF."""
    match = re.search(r'fy(\d{4})', pdf_path.stem)
    if not match:
        raise ValueError(f"Cannot determine FY from filename: {pdf_path.name}")
    fy = int(match.group(1))

    print(f"  Scraping FY {fy} ({pdf_path.name})...")
    pdf = pdfplumber.open(pdf_path)

    results = {}

    try:
        # Combined Budget Summary (all fund types)
        pages = find_combined_summary_pages(pdf)
        if pages:
            df = parse_combined_summary(pdf, pages, fy)
            if not df.empty:
                results["combined_summary"] = df
                print(f"    Combined Summary: {len(df)} rows across {len(pages)} pages")

        # All Funds Revenue (older format, more granular)
        pages = find_all_funds_revenue_pages(pdf)
        if pages:
            df = parse_all_funds_revenue(pdf, pages, fy)
            if not df.empty:
                results["all_funds_revenue"] = df
                print(f"    All Funds Revenue: {len(df)} rows across {len(pages)} pages")

        # General Fund departments
        pages = find_general_fund_summary_pages(pdf)
        if pages:
            df = parse_general_fund_depts(pdf, pages, fy)
            if not df.empty:
                results["general_fund_depts"] = df
                print(f"    General Fund Depts: {len(df)} rows across {len(pages)} pages")

    finally:
        pdf.close()

    return results


def scrape_all_budgets():
    """Scrape all downloaded budget PDFs and save combined datasets."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(PDF_DIR.glob("fy*-adopted-budget.pdf"))
    if not pdf_files:
        print(f"No PDFs found in {PDF_DIR}. Run download_budgets.py first.")
        return

    print(f"Found {len(pdf_files)} budget PDFs\n")

    all_revenue = []
    all_combined = []
    all_gf_depts = []

    for pdf_path in pdf_files:
        try:
            results = scrape_budget_pdf(pdf_path)
            if "all_funds_revenue" in results:
                all_revenue.append(results["all_funds_revenue"])
            if "combined_summary" in results:
                all_combined.append(results["combined_summary"])
            if "general_fund_depts" in results:
                all_gf_depts.append(results["general_fund_depts"])
        except Exception as e:
            print(f"  ERROR scraping {pdf_path.name}: {e}")

    # Save combined datasets
    if all_revenue:
        df = pd.concat(all_revenue, ignore_index=True)
        df.to_csv(OUTPUT_DIR / "all_funds_revenue.csv", index=False)
        print(f"\nSaved all_funds_revenue.csv ({len(df)} rows)")

    if all_combined:
        df = pd.concat(all_combined, ignore_index=True)
        df.to_csv(OUTPUT_DIR / "combined_budget_summary.csv", index=False)
        print(f"Saved combined_budget_summary.csv ({len(df)} rows)")

    if all_gf_depts:
        df = pd.concat(all_gf_depts, ignore_index=True)
        df.to_csv(OUTPUT_DIR / "general_fund_departments.csv", index=False)
        print(f"Saved general_fund_departments.csv ({len(df)} rows)")

    print("\nDone!")


if __name__ == "__main__":
    scrape_all_budgets()
