"""Explicit data-quality validation for canonical market and news schemas."""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


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
    required = ["date", "close", "volume"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        return ValidationResult(market_id, False, [f"missing required columns: {missing_cols}"], len(df))
    if len(df) == 0:
        return ValidationResult(market_id, False, ["zero rows returned"], 0)

    dates = pd.to_datetime(df["date"], errors="coerce")
    if dates.isna().any():
        issues.append(f"{int(dates.isna().sum())} unparseable date(s)")
    if dates.duplicated().any():
        issues.append(f"{int(dates.duplicated().sum())} duplicate date(s) for market_id={market_id}")

    numeric_cols = ["close", "volume"]
    null_counts = df[numeric_cols].isna().sum()
    for col, n in null_counts.items():
        if n:
            issues.append(f"{int(n)} null value(s) in '{col}'")

    clean = df.dropna(subset=numeric_cols)
    if (clean["close"] <= 0).any():
        issues.append(f"{int((clean['close'] <= 0).sum())} row(s) with close <= 0")
    if (clean["volume"] < 0).any():
        issues.append(f"{int((clean['volume'] < 0).sum())} row(s) with negative volume")

    ohlc = [c for c in ["open", "high", "low"] if c in df.columns]
    if len(ohlc) == 3:
        clean = df.dropna(subset=["open", "high", "low", "close"])
        if (clean["high"] < clean["low"]).any():
            issues.append(f"{int((clean['high'] < clean['low']).sum())} row(s) with high < low")
        if (clean["high"] < clean["open"]).any():
            issues.append(f"{int((clean['high'] < clean['open']).sum())} row(s) with high < open")
        if (clean["high"] < clean["close"]).any():
            issues.append(f"{int((clean['high'] < clean['close']).sum())} row(s) with high < close")
        if (clean["low"] > clean["open"]).any():
            issues.append(f"{int((clean['low'] > clean['open']).sum())} row(s) with low > open")
        if (clean["low"] > clean["close"]).any():
            issues.append(f"{int((clean['low'] > clean['close']).sum())} row(s) with low > close")

    return ValidationResult(market_id, len(issues) == 0, issues, len(df))


def validate_news(df: pd.DataFrame) -> ValidationResult:
    issues: list[str] = []
    required = ["article_id", "published_at", "title", "url"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        return ValidationResult("news", False, [f"missing required columns: {missing_cols}"], len(df))
    if len(df) == 0:
        return ValidationResult("news", False, ["zero rows returned"], 0)
    if df["article_id"].isna().any():
        issues.append(f"{int(df['article_id'].isna().sum())} null article_id(s)")
    if df["title"].isna().any() or (df["title"].astype(str).str.strip() == "").any():
        issues.append("row(s) with empty title")
    if df["url"].duplicated().any():
        issues.append(f"{int(df['url'].duplicated().sum())} duplicate url(s)")
    return ValidationResult("news", len(issues) == 0, issues, len(df))
