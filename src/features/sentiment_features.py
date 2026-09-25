"""Sentiment feature engineering, joined onto a market's own calendar. Days
with zero matched news are real information (no coverage that day), not
missing data to paper over: `news_volume` is 0 on those days, but
`sentiment_current` and friends stay NaN rather than being filled with a
fabricated neutral 0 — a day with no news is not evidence of neutral sentiment.
"""
from __future__ import annotations

import pandas as pd

from src.analytics.sentiment_stats import daily_sentiment

SENTIMENT_LAG_DAYS = (1, 3, 5)
ROLLING_SENTIMENT_WINDOW = 7

SENTIMENT_FEATURE_COLUMNS = [
    "sentiment_current", *[f"lag_sentiment_{lag}d" for lag in SENTIMENT_LAG_DAYS],
    f"rolling_mean_sentiment_{ROLLING_SENTIMENT_WINDOW}d", "sentiment_volatility",
    "positive_ratio", "negative_ratio", "news_volume",
]


def build_sentiment_features(entity_id: str, sentiment_df: pd.DataFrame, news_df: pd.DataFrame,
                              date_index: pd.Series, sentiment_model: str = "vader") -> pd.DataFrame:
    """`entity_id` is a company_id or crypto_asset_id (from
    `src.ingestion.universe.entity_to_market_map`). `date_index` is the full
    daily date range of the market series these features will be joined onto
    — every date in it gets a row here, matched or not, so the join in
    `pipeline.py` can never silently drop a trading day for lack of news.
    """
    entity_news = news_df[
        (news_df["matched_company_id"] == entity_id) | (news_df["matched_asset_id"] == entity_id)
    ]

    full = pd.DataFrame({"date": pd.to_datetime(pd.Series(date_index)).sort_values().unique()})

    if entity_news.empty:
        result = full.copy()
        for col in ["sentiment_current", "sentiment_volatility", "positive_ratio", "negative_ratio"]:
            result[col] = float("nan")  # float NaN, not pd.NA, so rolling()/downstream numeric ops work
        result["news_volume"] = 0
    else:
        daily = daily_sentiment(sentiment_df, entity_news, sentiment_model)
        daily["date"] = pd.to_datetime(daily["date"])
        result = full.merge(daily, on="date", how="left")
        result["news_volume"] = result["news_volume"].fillna(0)
        result = result.rename(columns={"mean_sentiment": "sentiment_current"})

    result = result.sort_values("date").reset_index(drop=True)
    for lag in SENTIMENT_LAG_DAYS:
        result[f"lag_sentiment_{lag}d"] = result["sentiment_current"].shift(lag)
    # rolling mean over calendar days with news; pandas .rolling().mean() skips
    # NaN entries within the window by construction, so this is the mean of
    # whatever news actually existed in the trailing window, not a fabricated fill.
    result[f"rolling_mean_sentiment_{ROLLING_SENTIMENT_WINDOW}d"] = (
        result["sentiment_current"].rolling(window=ROLLING_SENTIMENT_WINDOW, min_periods=1).mean()
    )

    return result[["date", *SENTIMENT_FEATURE_COLUMNS]]
