"""Validation for the combined feature table."""
from __future__ import annotations

import pandas as pd

from src.ingestion.validate import ValidationResult

REQUIRED_COLUMNS = ["market_id", "date", "return_1d", "log_return_1d"]


def validate_features(df: pd.DataFrame) -> ValidationResult:
    issues: list[str] = []

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        issues.append(f"missing required columns: {missing_cols}")
        return ValidationResult("features", False, issues, len(df))

    if len(df) == 0:
        issues.append("zero rows produced")
        return ValidationResult("features", False, issues, 0)

    dupes = df.duplicated(subset=["market_id", "date"]).sum()
    if dupes:
        issues.append(f"{dupes} duplicate (market_id, date) row(s)")

    for market_id, group in df.groupby("market_id"):
        if not group["date"].is_monotonic_increasing:
            issues.append(f"dates not monotonic increasing for market_id={market_id}")

    passed = len(issues) == 0
    return ValidationResult("features", passed, issues, len(df))
