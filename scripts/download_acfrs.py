"""
Download Annual Comprehensive Financial Reports (ACFR) from the City of San Antonio.
Source: https://www.sa.gov/Directory/Departments/Finance/Transparency/ACFR

Covers FY 2003 through FY 2024.
Note: Pre-2021 reports were called "CAFR" (Comprehensive Annual Financial Report).
"""

import os
import time
import requests
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "acfr_pdfs"

# Catalog of ACFR PDFs scraped from the Finance/Transparency/ACFR page.
# Two URL patterns: recent years use sa.gov/files/assets/..., older years use sanantonio.gov/Portals/...
ACFR_REPORTS = [
    # Recent reports (sa.gov domain)
    (2024, "https://www.sa.gov/files/assets/main/v/1/finance/documents/fy2024-annualcomprehensivefinancialreport.pdf"),
    (2023, "https://www.sa.gov/files/assets/main/v/1/finance/documents/fy2023-annualcomprehensivefinancialreport.pdf"),
    (2022, "https://www.sa.gov/files/assets/main/v/3/finance/documents/fy2022-annualcomprehensivefinancialreport.pdf"),
    (2021, "https://www.sa.gov/files/assets/main/v/1/finance/documents/fy2021-comprehensiveannualfinancialreport.pdf"),
    (2020, "https://www.sa.gov/files/assets/main/v/1/finance/documents/fy2020-comprehensiveannualfinancialreport.pdf"),
    # Historical reports (sanantonio.gov/Portals domain)
    (2019, "https://www.sanantonio.gov/Portals/0/Files/Finance/CAFR2019.pdf"),
    (2018, "https://www.sanantonio.gov/Portals/0/Files/Finance/CAFR2018.pdf"),
    (2017, "https://www.sanantonio.gov/Portals/0/Files/Finance/CAFR2017.pdf"),
    (2016, "https://www.sanantonio.gov/Portals/0/Files/Finance/CAFR2016.pdf"),
    (2015, "https://www.sanantonio.gov/Portals/0/Files/Finance/CAFR-2015.pdf"),
    (2014, "https://www.sanantonio.gov/Portals/0/Files/Finance/2014-CAFR.pdf"),
    (2013, "https://www.sanantonio.gov/Portals/0/Files/Finance/Website%20CAFR%202013.pdf"),
    (2012, "https://www.sanantonio.gov/Portals/0/Files/Finance/2012CAFR.pdf"),
    (2011, "https://www.sanantonio.gov/Portals/0/Files/Finance/FY%202011%20CAFR%20FINAL%20for%20Website.pdf"),
    (2010, "https://www.sanantonio.gov/Portals/0/Files/Finance/2010%20CAFR%20-%20COMPLETED.pdf"),
    (2009, "https://www.sanantonio.gov/Portals/0/Files/Finance/FY%202009%20CAFR.pdf"),
    (2008, "https://www.sanantonio.gov/Portals/0/Files/Finance/2008-CAFR.pdf"),
    (2007, "https://www.sanantonio.gov/Portals/0/Files/Finance/2007-CAFR.pdf"),
    (2006, "https://www.sanantonio.gov/Portals/0/Files/Finance/2006-CAFR.pdf"),
    (2005, "https://www.sanantonio.gov/Portals/0/Files/Finance/2005-CAFR.pdf"),
    (2004, "https://www.sanantonio.gov/Portals/0/Files/Finance/2004-CAFR.pdf"),
    (2003, "https://www.sanantonio.gov/Portals/0/Files/Finance/2003-CAFR.pdf"),
]


def download_pdf(year: int, url: str, output_dir: Path) -> Path | None:
    """Download a single ACFR PDF. Returns output path or None on failure."""
    output_path = output_dir / f"fy{year}-acfr.pdf"

    if output_path.exists():
        print(f"  [SKIP] FY {year} already downloaded ({output_path.name})")
        return output_path

    print(f"  [GET]  FY {year}: {url}")
    try:
        resp = requests.get(url, timeout=120, stream=True)
        resp.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = output_path.stat().st_size / (1024 * 1024)
        print(f"  [OK]   FY {year}: {size_mb:.1f} MB")
        return output_path

    except requests.RequestException as e:
        print(f"  [FAIL] FY {year}: {e}")
        if output_path.exists():
            output_path.unlink()
        return None


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(ACFR_REPORTS)} ACFR/CAFR PDFs")
    print(f"Output directory: {DATA_DIR}\n")

    results = {"ok": [], "fail": []}

    for year, url in ACFR_REPORTS:
        result = download_pdf(year, url, DATA_DIR)
        if result:
            results["ok"].append(year)
        else:
            results["fail"].append(year)
        time.sleep(1)  # be polite to the server

    print(f"\nDone: {len(results['ok'])} downloaded, {len(results['fail'])} failed")
    if results["fail"]:
        print(f"Failed years: {results['fail']}")


if __name__ == "__main__":
    main()
