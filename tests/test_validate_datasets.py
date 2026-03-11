import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.validate_datasets import DATA_DIR, DATASET_SPECS, validate_all, validate_dataset


def test_current_blessed_datasets_pass_validation():
    assert validate_all(DATA_DIR) == {}


def test_duplicate_primary_key_is_reported(tmp_path):
    spec = DATASET_SPECS["combined_budget_summary.csv"]
    frame = pd.read_csv(DATA_DIR / spec.filename)
    bad = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    bad.to_csv(tmp_path / spec.filename, index=False)

    errors = validate_dataset(tmp_path, spec)

    assert any("duplicate primary-key rows" in error for error in errors)


def test_missing_expected_year_is_reported(tmp_path):
    spec = DATASET_SPECS["cip_revenue_sources.csv"]
    frame = pd.read_csv(DATA_DIR / spec.filename)
    bad = frame[frame["fiscal_year"] != 2026]
    bad.to_csv(tmp_path / spec.filename, index=False)

    errors = validate_dataset(tmp_path, spec)

    assert any("expected fiscal years" in error for error in errors)
