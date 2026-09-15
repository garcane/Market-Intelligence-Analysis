"""Stage 8: chronological train/validation/test split. Never a random split —
the original repo's XGBoost notebook used `train_test_split(..., random_state=42)`
on time-series data (see PROJECT_AUDIT.md 3a), which is exactly the mistake
this module exists to make structurally impossible to repeat.

Boundary dates are calendar dates, applied identically across every asset
regardless of that asset's own trading calendar (crypto trades every day,
equities skip weekends) — this is deliberate: it keeps "what counts as the
test period" a single, asset-independent definition, rather than a different
cutoff row per asset.

Embargo: a target_h(t) resolves at date t+h, using a price that may fall on
the other side of a split boundary from t itself. A row at the end of the
train window can have a label that encodes validation-period information —
this is a real, easy-to-miss leakage vector, not a hypothetical one. Rows
whose OWN date falls in one window but whose TARGET resolves in the next are
excluded (embargoed) from that window entirely, using each row's exact
`target_date_{h}d` (from src/features/target.py) rather than a calendar-day
approximation.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Chosen to split the actual ingested history (2023-06-01 -> present) roughly
# 60/20/20 by calendar time. See SPLIT.md for the row-count breakdown that
# justifies these specific boundaries against the current dataset.
DEFAULT_TRAIN_END = "2025-05-31"
DEFAULT_VAL_END = "2026-01-31"


def assign_split(df: pd.DataFrame, horizon: int, train_end: str = DEFAULT_TRAIN_END,
                  val_end: str = DEFAULT_VAL_END) -> pd.Series:
    """Returns a Series of {"train", "validation", "test", "excluded_embargo",
    "excluded_no_target"} aligned to df's index. Requires `date` and
    `target_date_{h}d` columns (the latter from src.features.target.add_future_returns).
    """
    target_date_col = f"target_date_{horizon}d"
    if target_date_col not in df.columns:
        raise ValueError(f"{target_date_col} missing — call add_future_returns(horizons=({horizon},...)) first")

    date = pd.to_datetime(df["date"])
    target_date = pd.to_datetime(df[target_date_col])
    train_end_ts = pd.Timestamp(train_end)
    val_end_ts = pd.Timestamp(val_end)

    in_train_window = date <= train_end_ts
    in_val_window = (date > train_end_ts) & (date <= val_end_ts)
    in_test_window = date > val_end_ts
    has_target = target_date.notna()

    train_safe = in_train_window & has_target & (target_date <= train_end_ts)
    val_safe = in_val_window & has_target & (target_date <= val_end_ts)
    test_safe = in_test_window & has_target

    split = pd.Series("excluded_no_target", index=df.index)
    split[in_train_window] = "excluded_embargo"
    split[in_val_window] = "excluded_embargo"
    split[train_safe] = "train"
    split[val_safe] = "validation"
    split[test_safe] = "test"
    return split


def add_split_labels(df: pd.DataFrame, horizons: tuple[int, ...] = (1, 5, 10),
                      train_end: str = DEFAULT_TRAIN_END, val_end: str = DEFAULT_VAL_END) -> pd.DataFrame:
    """Adds one split_{h}d column per horizon — split boundaries and embargo
    are horizon-specific (a 10-day-ahead label needs a wider embargo than a
    1-day-ahead one), so a row can legitimately be "train" for horizon 1 and
    "excluded_embargo" for horizon 10 at the same date.
    """
    df = df.copy()
    for h in horizons:
        for market_id, group in df.groupby("market_id"):
            df.loc[group.index, f"split_{h}d"] = assign_split(group, h, train_end, val_end)
    return df


def walk_forward_folds(dates: pd.Series, n_folds: int, min_train_days: int,
                        test_days: int) -> list[tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]]:
    """Generates (train_end, test_start, test_end) boundaries for expanding-window
    walk-forward validation, for Stage 19's robustness testing — not used by the
    primary single-split experiment in this stage, but available for it.
    """
    unique_dates = pd.to_datetime(pd.Series(dates)).sort_values().unique()
    folds = []
    start_idx = min_train_days
    for _ in range(n_folds):
        if start_idx + test_days > len(unique_dates):
            break
        train_end = pd.Timestamp(unique_dates[start_idx - 1])
        test_start = pd.Timestamp(unique_dates[start_idx])
        test_end_idx = min(start_idx + test_days - 1, len(unique_dates) - 1)
        test_end = pd.Timestamp(unique_dates[test_end_idx])
        folds.append((train_end, test_start, test_end))
        start_idx += test_days
    return folds
