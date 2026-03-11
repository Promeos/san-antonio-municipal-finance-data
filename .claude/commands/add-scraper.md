Help build or extend a PDF scraper for a new data source.

If $ARGUMENTS specifies a target (e.g., "debt schedule", "personnel", "fee schedule"), start by:

1. Examining sample PDF pages to understand the table layout
2. Looking at existing scrapers in `src/` for patterns to follow
3. Writing the new scraper following project conventions:
   - Use pdfplumber for extraction
   - Output to `data/processed/` as a CSV
   - Include a `find_*_pages()` function for page detection
   - Include an `extract_*()` function for table parsing
   - Handle dollar amount parsing with the existing `extract_dollar_amount()` pattern from `src/scrape_budgets.py`

Test against a few PDFs and report extraction quality before running the full set.
