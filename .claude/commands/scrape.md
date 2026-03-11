Run the full data extraction pipeline. Activate the venv, then run each scraper in sequence:

1. `python src/scrape_budgets.py` — extract operating budget tables from PDFs
2. `python src/scrape_cip.py` — extract capital improvement program tables
3. `python src/scrape_acfr.py` — extract ACFR budget-vs-actual tables

After each step, report the number of rows written and any warnings. If a scraper fails, diagnose the error before continuing to the next one.

When all scrapers finish, run `wc -l data/processed/*.csv` and summarize the output dataset sizes.
