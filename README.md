# San Antonio Municipal Finance Data

This repository is an unofficial, reproducible data product for City of San Antonio municipal finance documents. It downloads official budget and ACFR PDFs, extracts structured tables from those PDFs, validates the resulting CSVs, and keeps the processed datasets under version control.

It is not affiliated with, endorsed by, or maintained by the City of San Antonio.

## What This Repo Publishes

The v1 public dataset contract covers these CSVs in `data/processed/`:

- `combined_budget_summary.csv`: all-funds and General Fund operating-budget totals by section and line item for FY 2008-FY 2026.
- `acfr_budget_vs_actual.csv`: General Fund budget-vs-actual rows from the ACFR budgetary comparison schedule for FY 2010-FY 2024.
- `cip_categories.csv`: capital program category totals for FY 2008-FY 2026.
- `bond_status.csv`: bond authorization, issued, and unissued rows for FY 2015-FY 2026.
- `cip_revenue_sources.csv`: capital program funding-source rows for FY 2011-FY 2015 and FY 2017-FY 2026.

Two processed datasets remain provisional and are not part of the release contract:

- `all_funds_revenue.csv`
- `general_fund_departments.csv`

See [docs/DATASET_CATALOG.md](docs/DATASET_CATALOG.md) for schemas, primary keys, coverage details, and caveats.

## Quick Start

Use Python 3.11 and the project virtual environment if you already have one:

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Download source documents:

```bash
venv/bin/python scripts/download_budgets.py
venv/bin/python scripts/download_acfrs.py
```

Regenerate processed datasets:

```bash
venv/bin/python src/scrape_budgets.py
venv/bin/python src/scrape_cip.py
venv/bin/python src/scrape_acfr.py
```

Validate the published contract:

```bash
venv/bin/python scripts/validate_datasets.py
pytest tests/test_validate_datasets.py tests/test_unit_scrapers.py -q
```

Stage release assets locally before publishing a GitHub release:

```bash
venv/bin/python scripts/stage_release_assets.py --version v1.0.0
```

## Repository Layout

- `src/`: PDF scraping code.
- `scripts/`: downloaders and validation entrypoints.
- `data/processed/`: tracked CSV outputs.
- `docs/`: dataset catalog and extraction methodology.
- `tests/`: PDF-backed scraper tests plus PDF-free contract/unit tests.
- `plans/`: implementation notes and living execution plans.

## CI Model

This repo uses two verification lanes:

- Fast CI on every push runs PDF-free unit tests and dataset-contract validation against the tracked CSVs.
- Integration CI is separate and downloads PDFs before running the parser regression suite.

## Downstream Analysis Repo

Analysis, notebooks, charts, and executive summaries live in the companion consumer repository `san-antonio-finance-analysis`. That repo fetches pinned CSV release assets from this data repo instead of duplicating extraction code.

## Licensing

- Code in this repository is licensed under [MIT](LICENSE).
- Processed datasets in `data/processed/` are licensed under [CC BY 4.0](DATA_LICENSE.md).
- Raw City PDFs remain subject to their original terms and are not relicensed by this repository.
