"""
Download adopted budget PDFs from the City of San Antonio Budget Archives.
Source: https://www.sa.gov/Directory/Departments/OMB/Budget-Archives

Covers FY 2000 through FY 2026.
"""

import os
import time
import requests
from pathlib import Path

BASE_URL = "https://www.sa.gov/files/assets/main/v"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "pdfs"

# Catalog of adopted budget PDFs scraped from the Budget Archives page.
# Format: (fiscal_year, relative_path_after_base_url)
ADOPTED_BUDGETS = [
    (2026, "8/omb/documents/fy2026/adopted-budget.pdf"),
    (2025, "1/omb/documents/fy2025/adopted-budget.pdf"),
    (2024, "1/omb/documents/fy2024/adopted-budget.pdf"),
    (2023, "2/omb/documents/fy2023/adopted-budget.pdf"),
    (2022, "1/omb/documents/fy2022/adopted-budget.pdf"),
    (2021, "1/omb/documents/fy2021/adopted-budget.pdf"),
    (2020, "1/omb/documents/fy2020/adopted-budget.pdf"),
    (2019, "1/omb/documents/fy2019/adopted-budget.pdf"),
    (2018, "1/omb/documents/fy2018/adopted-budget.pdf"),
    (2017, "1/omb/documents/fy2017/adopted-budget.pdf"),
    (2016, "1/omb/documents/fy2016/adopted-budget.pdf"),
    (2015, "1/omb/documents/fy2015/adopted-budget.pdf"),
    (2014, "1/omb/documents/fy2014/adopted-budget.pdf"),
    (2013, "1/omb/documents/fy2013/adopted-budget.pdf"),
    (2012, "1/omb/documents/fy2012/adopted-budget.pdf"),
    (2011, "1/omb/documents/fy2011/adopted-budget.pdf"),
    (2010, "1/omb/documents/fy2010/adopted-budget.pdf"),
    (2009, "1/omb/documents/fy2009/adopted-budget.pdf"),
    (2008, "1/omb/documents/fy2008/adopted-budget.pdf"),
    (2007, "1/omb/documents/fy2007/adopted-budget.pdf"),
    (2006, "1/omb/documents/fy2006/adopted-budget.pdf"),
    (2005, "1/omb/documents/fy2005-2000/fy2005-adopted-budget.pdf"),
    (2004, "1/omb/documents/fy2005-2000/fy2004-adopted-budget.pdf"),
    (2003, "1/omb/documents/fy2005-2000/fy2003-adopted-budget.pdf"),
    (2002, "1/omb/documents/fy2005-2000/fy2002-adopted-budget.pdf"),
    (2001, "1/omb/documents/fy2005-2000/fy2001-adopted-budget.pdf"),
    (2000, "1/omb/documents/fy2005-2000/fy2000-adopted-budget.pdf"),
]


def download_pdf(year: int, path: str, output_dir: Path) -> Path | None:
    """Download a single budget PDF. Returns output path or None on failure."""
    url = f"{BASE_URL}/{path}"
    output_path = output_dir / f"fy{year}-adopted-budget.pdf"

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

    print(f"Downloading {len(ADOPTED_BUDGETS)} adopted budget PDFs")
    print(f"Output directory: {DATA_DIR}\n")

    results = {"ok": [], "fail": []}

    for year, path in ADOPTED_BUDGETS:
        result = download_pdf(year, path, DATA_DIR)
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
