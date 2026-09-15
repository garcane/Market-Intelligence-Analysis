"""Cross-sectional features: market-wide and sector-wide return benchmarks,
and each asset's performance relative to them. These use same-day returns
across the ingested universe — contemporaneous, not future, information (every
asset's return_1d at date t is itself only a function of prices up to t), so
this is leakage-safe under the same rule as the single-asset features.

Note: with a small universe (single digits of assets), an asset is a
non-trivial share of its own benchmark (e.g. 1/6 in a 6-asset universe) —
documented in FEATURES.md, not something this module tries to correct for
(equal-weighted, include-self is the standard convention and what's implemented
here; it only becomes materially distorting once the universe is large enough
that leave-one-out no longer matters, which will be revisited if/when the
tracked universe grows well beyond its current size).
"""
from __future__ import annotations

import pandas as pd


def build_returns_wide(market_returns: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """market_returns: {market_id: df with [date, return_1d]}. Returns a wide
    date x market_id frame of return_1d."""
    series = {mid: df.set_index("date")["return_1d"] for mid, df in market_returns.items()}
    return pd.DataFrame(series)


def compute_market_return(returns_wide: pd.DataFrame) -> pd.Series:
    return returns_wide.mean(axis=1, skipna=True).rename("market_return")


def compute_ai_index_return(returns_wide: pd.DataFrame, equity_market_ids: list[str]) -> pd.Series:
    cols = [c for c in equity_market_ids if c in returns_wide.columns]
    return returns_wide[cols].mean(axis=1, skipna=True).rename("ai_index_return")


def compute_sector_returns(returns_wide: pd.DataFrame, sector_members: dict[str, list[str]]) -> pd.DataFrame:
    """sector_members: {sector_label: [market_id, ...]}."""
    out = {}
    for sector, members in sector_members.items():
        cols = [c for c in members if c in returns_wide.columns]
        if cols:
            out[sector] = returns_wide[cols].mean(axis=1, skipna=True)
    return pd.DataFrame(out, index=returns_wide.index)


def add_cross_sectional_features(asset_df: pd.DataFrame, market_return: pd.Series,
                                  ai_index_return: pd.Series,
                                  sector_return: pd.Series | None = None) -> pd.DataFrame:
    df = asset_df.copy()
    df = df.merge(market_return.reset_index(), on="date", how="left")
    df = df.merge(ai_index_return.reset_index(), on="date", how="left")
    df["relative_performance"] = df["return_1d"] - df["market_return"]
    if sector_return is not None:
        df = df.merge(sector_return.rename("sector_return").reset_index(), on="date", how="left")
        df["relative_sector_performance"] = df["return_1d"] - df["sector_return"]
    return df
