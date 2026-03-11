# San Antonio City Budget Project

## Project Context
Data science project analyzing City of San Antonio finances (FY 2000–2026).
Budget data is scraped from PDF documents — the city has no machine-readable finance datasets.
SA fiscal year runs Oct 1 – Sep 30.

## Tech Stack
- Python 3.11, virtualenv at `./venv`
- Key libraries: pdfplumber, pandas, matplotlib, jupyter
- Always activate venv before running Python: `source venv/bin/activate`

## Project Structure
- `scripts/` — downloaders and report generators (entry points)
- `src/` — scraping modules (pdfplumber-based extractors)
- `data/pdfs/` and `data/acfr_pdfs/` — source PDFs
- `data/processed/` — extracted CSVs (canonical outputs)
- `notebooks/` — Jupyter exploration notebooks
- `figures/` — standalone chart PNGs
- `reports/` — generated reports (executive summary)

## Key Conventions
- `combined_budget_summary.csv` is the canonical source for executive trend reporting
- Dollar amounts in CSVs are raw floats (not formatted) — format for display only
- Scraper outputs go to `data/processed/`; never edit CSVs by hand
- Charts use the project color palette defined in `scripts/generate_executive_summary.py`

## Data Quality Notes
- FY 2000–2007 PDFs have a different format and are not yet parsed
- `general_fund_departments.csv` has reconciliation issues — not reliable for headlines
- `all_funds_revenue.csv` needs normalization before use — fund labels are inconsistent
- ACFR coverage has a gap: FY 2011–2014 tables were not text-extractable
