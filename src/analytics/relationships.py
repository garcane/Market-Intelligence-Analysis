"""Sentiment <-> market relationship analysis. Every function here returns a
correlation, not a causal claim — see the caveat printed alongside every result
in run_eda.py. Per the target spec: "Do not claim causality from correlation."
"""
from __future__ import annotations

import pandas as pd


def merge_sentiment_and_market(daily_sentiment_df: pd.DataFrame, market_stats_df: pd.DataFrame) -> pd.DataFrame:
    """Same-day join of daily aggregated sentiment against market stats.
    Both frames must already have a `date` column of the same dtype.
    """
    sent = daily_sentiment_df.copy()
    sent["date"] = pd.to_datetime(sent["date"])
    mkt = market_stats_df.copy()
    mkt["date"] = pd.to_datetime(mkt["date"])
    return sent.merge(mkt, on="date", how="inner")


def sentiment_return_correlation(merged_df: pd.DataFrame) -> dict:
    n = len(merged_df)
    if n < 3:
        return {"n_obs": n, "correlation": float("nan"), "note": "insufficient overlapping observations"}
    corr = merged_df["mean_sentiment"].corr(merged_df["return_1d"])
    return {"n_obs": n, "correlation": float(corr) if pd.notna(corr) else float("nan")}


def news_volume_volatility_correlation(merged_df: pd.DataFrame) -> dict:
    n = len(merged_df)
    vol_col = "rolling_vol_7d" if "rolling_vol_7d" in merged_df.columns else None
    if n < 3 or vol_col is None:
        return {"n_obs": n, "correlation": float("nan"), "note": "insufficient overlapping observations"}
    corr = merged_df["news_volume"].corr(merged_df[vol_col])
    return {"n_obs": n, "correlation": float(corr) if pd.notna(corr) else float("nan")}
