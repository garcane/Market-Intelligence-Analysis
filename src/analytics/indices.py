"""Stage 12: thematic AI equity indices, built from real ingested constituent
prices (equal-weighted — no market-cap data reliably available across this
mixed universe, so equal-weight is the defensible, documented default).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

RISK_FREE_RATE_ANNUAL = 0.0  # simplifying assumption, documented in INDICES.md

# Membership drawn directly from data/reference/{companies,company_ai_categories}.csv
# (Stage 1), restricted to what's actually been ingested (data/raw/market_prices/).
INDEX_MEMBERS = {
    "ai_infrastructure_index": ["NVDA", "AMD", "AVGO", "TSM", "MU"],
    "ai_platform_index": ["MSFT", "AMZN", "GOOGL", "META", "AAPL", "ORCL"],
    "ai_model_provider_index": ["MSFT", "GOOGL", "META"],
}

BENCHMARK_IDS = ["SPX", "NASDAQ", "SOXX", "BTC", "ETH"]


def build_index_return(returns_wide: pd.DataFrame, members: list[str]) -> pd.Series:
    available = [m for m in members if m in returns_wide.columns]
    if not available:
        raise ValueError(f"none of {members} are in the ingested universe")
    return returns_wide[available].mean(axis=1, skipna=True)


def cumulative_return(returns: pd.Series) -> pd.Series:
    return (1 + returns.fillna(0)).cumprod() - 1


def max_drawdown(returns: pd.Series) -> float:
    cum = (1 + returns.fillna(0)).cumprod()
    running_max = cum.cummax()
    drawdown = cum / running_max - 1
    return float(drawdown.min())


def annualized_sharpe(returns: pd.Series, periods_per_year: int = 365) -> float:
    """365 (not 252) is used throughout this module since the mixed
    equity+crypto universe includes assets that trade every calendar day —
    documented in INDICES.md rather than silently picking one convention."""
    excess = returns.dropna() - RISK_FREE_RATE_ANNUAL / periods_per_year
    if excess.std() == 0 or len(excess) < 2:
        return float("nan")
    return float(excess.mean() / excess.std() * np.sqrt(periods_per_year))


def rolling_correlation(a: pd.Series, b: pd.Series, window: int = 30) -> pd.Series:
    return a.rolling(window).corr(b)


def beta(index_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    aligned = pd.concat([index_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2 or aligned.iloc[:, 1].var() == 0:
        return float("nan")
    cov = aligned.cov().iloc[0, 1]
    var = aligned.iloc[:, 1].var()
    return float(cov / var)


def index_summary(returns: pd.Series) -> dict:
    return {
        "annualized_volatility": float(returns.std() * np.sqrt(365)),
        "cumulative_return": float(cumulative_return(returns).iloc[-1]) if len(returns) else float("nan"),
        "max_drawdown": max_drawdown(returns),
        "sharpe_ratio": annualized_sharpe(returns),
    }
