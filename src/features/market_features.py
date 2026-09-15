"""Market feature engineering. Every function here is strictly causal: a value
in row t is a function of rows <= t only (`.rolling()` with the pandas default
right-aligned window, `.shift()` for lags, never `center=True` or any operation
that reads ahead of the current row). This is the leakage-safety contract Rule 4
of the target spec demands, and `tests/test_features.py` enforces it with a
regression test that mutates future rows and asserts past feature rows don't move.

Built directly on `src.analytics.market_stats`'s already-causal return/drawdown
primitives rather than recomputing them, so EDA and modelling never disagree
on what "return" or "drawdown" means.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.analytics.market_stats import add_drawdown, add_returns, add_rolling_volatility

LAG_DAYS = (1, 3, 5, 10)
ROLLING_RETURN_WINDOWS = (5, 10, 30)
MOVING_AVERAGE_WINDOWS = (10, 30, 50)
MOMENTUM_WINDOWS = (10, 30)
RSI_WINDOW = 14
VOLUME_WINDOW = 10


def add_lagged_returns(df: pd.DataFrame, lags: tuple[int, ...] = LAG_DAYS) -> pd.DataFrame:
    df = df.copy()
    for lag in lags:
        df[f"lag_return_{lag}d"] = df["return_1d"].shift(lag)
    return df


def add_rolling_returns(df: pd.DataFrame, price_col: str = "close",
                         windows: tuple[int, ...] = ROLLING_RETURN_WINDOWS) -> pd.DataFrame:
    """N-day trailing price change: price(t) / price(t-N) - 1."""
    df = df.copy()
    for w in windows:
        df[f"rolling_return_{w}d"] = df[price_col] / df[price_col].shift(w) - 1.0
    return df


def add_moving_averages(df: pd.DataFrame, price_col: str = "close",
                         windows: tuple[int, ...] = MOVING_AVERAGE_WINDOWS) -> pd.DataFrame:
    df = df.copy()
    for w in windows:
        df[f"sma_{w}d"] = df[price_col].rolling(window=w).mean()
    return df


def add_momentum(df: pd.DataFrame, price_col: str = "close",
                  windows: tuple[int, ...] = MOMENTUM_WINDOWS) -> pd.DataFrame:
    """Distance of current price from its own N-day moving average — a
    normalized trend-strength signal, distinct from raw rolling_return."""
    df = df.copy()
    for w in windows:
        sma = df[price_col].rolling(window=w).mean()
        df[f"momentum_{w}d"] = df[price_col] / sma - 1.0
    return df


def add_rsi(df: pd.DataFrame, price_col: str = "close", window: int = RSI_WINDOW) -> pd.DataFrame:
    """Classic Wilder RSI on `window`-day trailing gains/losses. Uses
    `.rolling().mean()` (not the exponential Wilder smoothing variant) for a
    simple, auditable, strictly backward-looking implementation."""
    df = df.copy()
    delta = df[price_col].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # where avg_loss == 0 and avg_gain > 0, RSI is defined as 100 (all gains, no losses)
    rsi = rsi.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
    df[f"rsi_{window}d"] = rsi
    return df


def add_volume_features(df: pd.DataFrame, window: int = VOLUME_WINDOW) -> pd.DataFrame:
    df = df.copy()
    df["volume_change_1d"] = df["volume"].pct_change()
    rolling_mean_volume = df["volume"].rolling(window=window).mean()
    df[f"volume_ratio_{window}d"] = df["volume"] / rolling_mean_volume - 1.0
    return df


def build_market_features(df: pd.DataFrame) -> pd.DataFrame:
    """Full market feature pipeline for one asset's OHLCV history.
    Input: [date, open, high, low, close, volume, ...]. Output: input columns
    plus all derived features, one row per date, sorted ascending by date.
    """
    df = df.sort_values("date").reset_index(drop=True)
    df = add_returns(df)
    df = add_rolling_volatility(df)
    df = add_drawdown(df)
    df = add_lagged_returns(df)
    df = add_rolling_returns(df)
    df = add_moving_averages(df)
    df = add_momentum(df)
    df = add_rsi(df)
    df = add_volume_features(df)
    return df
