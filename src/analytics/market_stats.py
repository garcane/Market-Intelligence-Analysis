"""Descriptive market statistics for EDA: returns, log returns, rolling
volatility, drawdown. All computed strictly from past-and-present data at each
row (no look-ahead) — this module is reused unchanged by the Stage 6 feature
pipeline, so leakage-safety here matters beyond just EDA correctness.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_returns(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    df = df.sort_values("date").copy()
    df["return_1d"] = df[price_col].pct_change()
    df["log_return_1d"] = np.log(df[price_col] / df[price_col].shift(1))
    return df


def add_rolling_volatility(df: pd.DataFrame, windows: tuple[int, ...] = (7, 30)) -> pd.DataFrame:
    df = df.copy()
    for w in windows:
        df[f"rolling_vol_{w}d"] = df["log_return_1d"].rolling(window=w).std()
    return df


def add_drawdown(df: pd.DataFrame, price_col: str = "close") -> pd.DataFrame:
    df = df.sort_values("date").copy()
    running_max = df[price_col].cummax()
    df["drawdown"] = df[price_col] / running_max - 1.0
    return df


def add_cumulative_return(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["cumulative_return"] = (1 + df["return_1d"].fillna(0)).cumprod() - 1
    return df


def compute_market_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Full descriptive pipeline: returns -> volatility -> drawdown -> cum return."""
    df = add_returns(df)
    df = add_rolling_volatility(df)
    df = add_drawdown(df)
    df = add_cumulative_return(df)
    return df


def summary_stats(df: pd.DataFrame) -> dict:
    return {
        "n_days": len(df),
        "start_date": str(df["date"].min().date()),
        "end_date": str(df["date"].max().date()),
        "mean_daily_return": float(df["return_1d"].mean()),
        "annualized_volatility": float(df["log_return_1d"].std() * np.sqrt(252)),
        "max_drawdown": float(df["drawdown"].min()),
        "total_return": float(df["cumulative_return"].iloc[-1]) if len(df) else float("nan"),
    }
