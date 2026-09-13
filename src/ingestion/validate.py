"""Data-quality validation for market price data. Validation never silently
passes bad data through — every check returns explicit pass/fail plus the
offending rows, and the caller decides whether to store, quarantine, or reject.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


@dataclass
class ValidationResult:
    market_id: str
    passed: bool
    issues: list[str] = field(default_factory=list)
    row_count: int = 0

    def __bool__(self) -> bool:
        return self.passed


def validate_market_prices(df: pd.DataFrame, market_id: str) -> ValidationResult:
    issues: list[str] = []

    # 1. Schema
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        issues.append(f"missing required columns: {missing_cols}")
        return ValidationResult(market_id, False, issues, len(df))

    # 2. Row count
    if len(df) == 0:
        issues.append("zero rows returned")
        return ValidationResult(market_id, False, issues, 0)

    # 3. Dates: parseable, no duplicates, monotonic-safe (sorted check happens at store time)
    dates = pd.to_datetime(df["date"], errors="coerce")
    n_bad_dates = dates.isna().sum()
    if n_bad_dates:
        issues.append(f"{n_bad_dates} unparseable date(s)")

    # 4. Duplicates on the fact grain (market_id, date)
    n_dupe_dates = dates.duplicated().sum()
    if n_dupe_dates:
        issues.append(f"{n_dupe_dates} duplicate date(s) for market_id={market_id}")

    # 5. Nulls in required numeric columns
    numeric_cols = ["open", "high", "low", "close", "volume"]
    null_counts = df[numeric_cols].isna().sum()
    for col, n in null_counts.items():
        if n:
            issues.append(f"{n} null value(s) in '{col}'")

    # 6. Value ranges / OHLC consistency (only on rows with complete numeric data)
    clean = df.dropna(subset=numeric_cols)
    if (clean["close"] <= 0).any():
        issues.append(f"{(clean['close'] <= 0).sum()} row(s) with close <= 0")
    if (clean["volume"] < 0).any():
        issues.append(f"{(clean['volume'] < 0).sum()} row(s) with negative volume")
    if (clean["high"] < clean["low"]).any():
        issues.append(f"{(clean['high'] < clean['low']).sum()} row(s) with high < low")
    if (clean["high"] < clean["open"]).any():
        issues.append(f"{(clean['high'] < clean['open']).sum()} row(s) with high < open")
    if (clean["high"] < clean["close"]).any():
        issues.append(f"{(clean['high'] < clean['close']).sum()} row(s) with high < close")
    if (clean["low"] > clean["open"]).any():
        issues.append(f"{(clean['low'] > clean['open']).sum()} row(s) with low > open")
    if (clean["low"] > clean["close"]).any():
        issues.append(f"{(clean['low'] > clean['close']).sum()} row(s) with low > close")

    passed = len(issues) == 0
    return ValidationResult(market_id, passed, issues, len(df))


def validate_news(df: pd.DataFrame) -> ValidationResult:
    issues: list[str] = []
    required = ["timestamp", "source_id", "title", "url"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        issues.append(f"missing required columns: {missing_cols}")
        return ValidationResult("news", False, issues, len(df))

    if len(df) == 0:
        issues.append("zero rows returned")
        return ValidationResult("news", False, issues, 0)

    n_null_title = df["title"].isna().sum() + (df["title"].str.strip() == "").sum()
    if n_null_title:
        issues.append(f"{n_null_title} row(s) with empty title")

    n_dupe_url = df["url"].duplicated().sum()
    if n_dupe_url:
        issues.append(f"{n_dupe_url} duplicate url(s)")

    passed = len(issues) == 0
    return ValidationResult("news", passed, issues, len(df))
