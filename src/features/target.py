"""Classification target construction (Stage 7). This is the ONE module in the
codebase that is deliberately forward-looking — `add_future_returns` uses
`.shift(-h)`, the mirror image of every other feature's `.shift(+h)`. It is
kept structurally separate from `src/features/pipeline.py` (which only ever
produces features(t)) precisely so a future stage can never accidentally merge
a target column into the feature table and call it a feature.

Per Rule 4 of the target spec: features(t) -> target = return(t -> t+h). The
last h rows of every asset's date range have no known future price and get a
NaN target — they are real rows with an undefined label, not zero-filled.
"""
from __future__ import annotations

import pandas as pd

HORIZONS = (1, 5, 10)
PRIMARY_HORIZON = 5
# See TARGET.md for the empirical justification of this threshold.
DEFAULT_THRESHOLD = 0.02


def add_future_returns(df: pd.DataFrame, horizons: tuple[int, ...] = HORIZONS,
                        price_col: str = "close") -> pd.DataFrame:
    """future_return_{h}d(t) = price(t+h) / price(t) - 1. Forward-looking by
    design (this is the label, not a feature) — NaN for the last h rows of
    each asset, where price(t+h) doesn't exist in the ingested history yet.
    """
    df = df.sort_values("date").reset_index(drop=True).copy()
    for h in horizons:
        df[f"future_return_{h}d"] = df[price_col].shift(-h) / df[price_col] - 1.0
        # The calendar date the target actually resolves on — needed by
        # src/models/split.py to embargo rows whose label peeks past a split
        # boundary (row-exact, not a calendar-day approximation).
        df[f"target_date_{h}d"] = df["date"].shift(-h)
    return df


def add_classification_targets(df: pd.DataFrame, horizons: tuple[int, ...] = HORIZONS,
                                threshold: float | dict[int, float] = DEFAULT_THRESHOLD) -> pd.DataFrame:
    """target_{h}d = 1 if future_return_{h}d > threshold, 0 if <= threshold,
    NaN if future_return_{h}d is itself NaN (undefined label, never fabricated
    as 0). `threshold` may be one float applied to every horizon, or a
    {horizon: threshold} dict for per-horizon thresholds.
    """
    df = df.copy()
    for h in horizons:
        col = f"future_return_{h}d"
        if col not in df.columns:
            raise ValueError(f"{col} missing — call add_future_returns first")
        t = threshold[h] if isinstance(threshold, dict) else threshold
        target = (df[col] > t).astype("float64")
        target[df[col].isna()] = float("nan")
        df[f"target_{h}d"] = target
    return df


def build_target_table(market_prices: dict[str, pd.DataFrame], horizons: tuple[int, ...] = HORIZONS,
                        threshold: float | dict[int, float] = DEFAULT_THRESHOLD) -> pd.DataFrame:
    """market_prices: {market_id: OHLCV df}. Returns one long table:
    market_id, date, future_return_{h}d, target_{h}d for every horizon.
    Kept separate from src/features/pipeline.py's feature table by design.
    """
    frames = []
    for market_id, df in market_prices.items():
        with_returns = add_future_returns(df[["date", "close"]], horizons)
        with_targets = add_classification_targets(with_returns, horizons, threshold)
        with_targets.insert(0, "market_id", market_id)
        frames.append(with_targets)
    result = pd.concat(frames, ignore_index=True)
    return result.sort_values(["market_id", "date"]).reset_index(drop=True)
