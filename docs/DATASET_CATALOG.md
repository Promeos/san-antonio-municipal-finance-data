# Dataset Catalog

This catalog describes the published CSV contract for the unofficial San Antonio municipal finance data repository.

## Blessed Datasets

### `combined_budget_summary.csv`

- Purpose: operating-budget summary rows reconstructed from adopted budget PDFs.
- Coverage: FY 2008-FY 2026.
- Columns:
  - `section` (`balance`, `revenue`, `appropriation`)
  - `line_item` (string)
  - `amount` (float, dollars)
  - `fund` (string; current extractor publishes `General Fund` and `Total All Funds`)
  - `fiscal_year` (integer)
- Primary key: `fiscal_year + fund + section + line_item`
- Notes: this is the strongest operating-budget dataset in the repo and the default source for top-line reporting.

### `acfr_budget_vs_actual.csv`

- Purpose: General Fund budgetary comparison rows from ACFR PDFs.
- Coverage: FY 2010-FY 2024.
- Columns:
  - `fiscal_year`
  - `section` (`revenue`, `expenditure`)
  - `line_item`
  - `original_budget`
  - `final_budget`
  - `actual`
  - `variance`
- Primary key: `fiscal_year + section + line_item`
- Notes: revenue variance is stored as `actual - final_budget`; expenditure variance is stored as `final_budget - actual`, matching the statement presentation.

### `cip_categories.csv`

- Purpose: capital program category totals from adopted budget PDFs.
- Coverage: FY 2008-FY 2026.
- Columns:
  - `category`
  - `fy_amount`
  - `multiyear_amount`
  - `fiscal_year`
- Primary key: `fiscal_year + category`
- Notes: `multiyear_amount` is null in years where the table only exposed annual totals.

### `bond_status.csv`

- Purpose: bond authorization, issuance, and unissued balances from budget bond-status tables.
- Coverage: FY 2015-FY 2026.
- Columns:
  - `bond_program`
  - `proposition`
  - `authorized`
  - `issued`
  - `unissued`
  - `fiscal_year`
- Primary key: `fiscal_year + bond_program + proposition`
- Notes: three FY 2022 proposition rows do not expose issued and unissued values cleanly in the source table, so those fields are null in the tracked CSV.

### `cip_revenue_sources.csv`

- Purpose: capital program funding-source rows from adopted budget PDFs.
- Coverage: FY 2011-FY 2015 and FY 2017-FY 2026.
- Columns:
  - `source`
  - `fy_amount`
  - `multiyear_amount`
  - `fiscal_year`
- Primary key: `fiscal_year + source`
- Notes: FY 2011-FY 2014 and FY 2017 only expose total rows. FY 2016 is currently missing because the parser does not identify a usable revenue-source table in that PDF.

## Provisional Datasets

These files stay in `data/processed/` for exploration and debugging, but they are not part of the release contract and are not published as v1 release assets.

### `all_funds_revenue.csv`

- Purpose: more granular operating-budget revenue rows grouped by fund.
- Coverage: FY 2008-FY 2026.
- Current status: canonical fund labels and raw fund provenance are preserved, but row completeness still needs reconciliation across years.

### `general_fund_departments.csv`

- Purpose: department-level General Fund appropriations from adopted budget PDFs.
- Coverage: FY 2008-FY 2026.
- Current status: useful for exploration, but some years still contain extraction artifacts and reconciliation gaps relative to `combined_budget_summary.csv`.

## Release Expectations

- Breaking schema changes to blessed datasets require a new tagged release and an updated catalog.
- Release assets should include only the five blessed CSVs.
