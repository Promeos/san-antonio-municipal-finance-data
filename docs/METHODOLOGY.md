# Methodology

## What This Repository Does

The City of San Antonio publishes core budget and financial documents as PDFs. This repository turns those PDFs into machine-readable datasets by:

1. downloading official budget and ACFR PDFs,
2. locating relevant pages with text heuristics,
3. parsing dollar amounts and row labels with `pdfplumber`,
4. writing normalized CSVs to `data/processed/`, and
5. validating the published dataset contract before release.

## Source Documents

- Adopted budget PDFs: downloaded by `scripts/download_budgets.py` into `data/pdfs/`
- ACFR PDFs: downloaded by `scripts/download_acfrs.py` into `data/acfr_pdfs/`

Raw PDFs are intentionally gitignored. The tracked product is the processed CSV layer in `data/processed/`.

## Regeneration Commands

From the repository root:

```bash
venv/bin/python scripts/download_budgets.py
venv/bin/python scripts/download_acfrs.py
venv/bin/python src/scrape_budgets.py
venv/bin/python src/scrape_cip.py
venv/bin/python src/scrape_acfr.py
venv/bin/python scripts/validate_datasets.py
```

If you want the provisional revenue dataset check as well:

```bash
venv/bin/python scripts/validate_all_funds_revenue.py
```

## Extraction Approach

- `src/scrape_budgets.py` extracts the combined budget summary, all-funds revenue table, and General Fund department summary.
- `src/scrape_cip.py` extracts capital program categories, capital funding sources, and bond program status tables.
- `src/scrape_acfr.py` extracts the General Fund budgetary comparison schedule from ACFR PDFs.

The scrapers use page-finding heuristics first, then parse extracted text or tables into normalized rows. The row-level logic is intentionally explicit instead of using generic OCR-style inference because the PDF layouts shift across fiscal years.

## Validation Model

Two validation lanes exist:

- Fast contract validation:
  - runs PDF-free unit tests,
  - validates tracked blessed CSVs for schema, keys, coverage, and dataset-specific sanity rules.
- Integration validation:
  - downloads PDFs,
  - runs the PDF-backed scraper regression tests,
  - is suitable for scheduled or manual verification.

## Extending Coverage

When adding a new fiscal year or a new table type:

1. download the source PDF,
2. add or adjust the page-finding logic in the relevant scraper,
3. regenerate the affected CSV,
4. update `docs/DATASET_CATALOG.md` if coverage or schema changed,
5. add or update tests, and
6. rerun `scripts/validate_datasets.py`.
