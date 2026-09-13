"""Storage + round-trip integrity checking. Every ingestion run must prove that
what was stored matches what was fetched (fetch -> store -> reload -> compare),
per the ingestion agentic loop in the target spec.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.config import RAW_DIR


def market_prices_path(market_id: str) -> Path:
    safe_id = market_id.replace("/", "_")
    return RAW_DIR / "market_prices" / f"{safe_id}.parquet"


def news_path() -> Path:
    return RAW_DIR / "news" / "news.parquet"


def save_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def load_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def round_trip_matches(original: pd.DataFrame, path: Path) -> tuple[bool, list[str]]:
    """Save `original` to `path`, reload it, and compare. Returns (matches, issues)."""
    save_parquet(original, path)
    reloaded = load_parquet(path)

    issues: list[str] = []
    if len(reloaded) != len(original):
        issues.append(f"row count mismatch: original={len(original)} reloaded={len(reloaded)}")
    if list(reloaded.columns) != list(original.columns):
        issues.append(f"column mismatch: original={list(original.columns)} reloaded={list(reloaded.columns)}")
    if not issues:
        # Compare values, not dtypes: parquet round-trips routinely change dtype
        # (datetime64 unit shifts, object -> pandas "string" dtype) and missing-value
        # sentinel (None -> NaN / pd.NA) without changing the represented data.
        # assert_frame_equal(check_dtype=False) is the well-tested tool for exactly
        # this: value/NaN-aware equality that tolerates dtype-only differences.
        left = original.reset_index(drop=True)
        right = reloaded.reset_index(drop=True)
        if "date" in left.columns:
            left = left.assign(date=pd.to_datetime(left["date"]))
            right = right.assign(date=pd.to_datetime(right["date"]))
        # Normalize every missing-value sentinel (pd.NA / None / NaT) to plain
        # float NaN so pd.NA vs None differences aren't reported as mismatches.
        left = left.where(left.notna(), np.nan)
        right = right.where(right.notna(), np.nan)
        try:
            pd.testing.assert_frame_equal(left, right, check_dtype=False, check_exact=False)
        except AssertionError as exc:
            issues.append(f"value mismatch after reload: {exc}")

    return (len(issues) == 0), issues
