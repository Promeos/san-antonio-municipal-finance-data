Validate the extracted datasets in `data/processed/`. For each CSV:

1. Load the file with pandas
2. Report: row count, column names, fiscal year range, any null values
3. Check for obvious issues:
   - Duplicate rows
   - Fiscal years outside the expected range (2000–2026)
   - Negative dollar amounts that shouldn't be negative
   - Total rows that don't reconcile with detail rows (where applicable)

Cross-check `combined_budget_summary.csv` General Fund totals against `general_fund_departments.csv` totals for overlapping fiscal years. Report any discrepancies.

Summarize findings as a table: dataset, rows, year range, issues found.
