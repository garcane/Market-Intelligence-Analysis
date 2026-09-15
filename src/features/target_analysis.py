"""Empirical threshold/horizon analysis to justify the classification target's
threshold, rather than picking one arbitrarily (per Stage 7's explicit
instruction: "the exact threshold should be tested and justified"). Also
reports each asset's own realized volatility so a fixed threshold's
reasonableness can be judged against assets with very different baseline
volatility (equities vs crypto).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.target import add_classification_targets, add_future_returns

CANDIDATE_THRESHOLDS = (0.0, 0.01, 0.02, 0.03, 0.05)
CANDIDATE_HORIZONS = (1, 5, 10)


def class_balance_grid(market_prices: dict[str, pd.DataFrame],
                        horizons: tuple[int, ...] = CANDIDATE_HORIZONS,
                        thresholds: tuple[float, ...] = CANDIDATE_THRESHOLDS) -> pd.DataFrame:
    """One row per (market_id, horizon, threshold): n_obs, positive_rate."""
    rows = []
    for market_id, df in market_prices.items():
        with_returns = add_future_returns(df[["date", "close"]], horizons)
        for h in horizons:
            col = f"future_return_{h}d"
            valid = with_returns[col].dropna()
            for t in thresholds:
                positive_rate = float((valid > t).mean()) if len(valid) else float("nan")
                rows.append({
                    "market_id": market_id, "horizon": h, "threshold": t,
                    "n_obs": len(valid), "positive_rate": positive_rate,
                })
    return pd.DataFrame(rows)


def realized_volatility_by_asset(market_prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Daily and horizon-scaled (sqrt-time) realized volatility per asset, for
    judging whether a fixed threshold is a comparable number of standard
    deviations across assets with very different baseline volatility.
    """
    rows = []
    for market_id, df in market_prices.items():
        close = df.sort_values("date")["close"]
        log_ret = np.log(close / close.shift(1)).dropna()
        daily_vol = float(log_ret.std())
        rows.append({
            "market_id": market_id,
            "daily_vol": daily_vol,
            "vol_5d": daily_vol * np.sqrt(5),
            "vol_10d": daily_vol * np.sqrt(10),
        })
    return pd.DataFrame(rows)
