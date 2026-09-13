"""Descriptive sentiment statistics for EDA: distribution, time series,
by-entity breakdowns.
"""
from __future__ import annotations

import pandas as pd


def daily_sentiment(sentiment_long_df: pd.DataFrame, news_df: pd.DataFrame,
                     sentiment_model: str = "vader") -> pd.DataFrame:
    """Aggregates sentiment to one row per calendar date: mean score, article
    count, positive/negative ratios. `news_df` supplies the timestamp per news_id.
    """
    scored = sentiment_long_df[sentiment_long_df["sentiment_model"] == sentiment_model]
    merged = scored.merge(news_df[["news_id", "timestamp", "matched_company_id", "matched_asset_id"]],
                           on="news_id", how="left")
    merged["date"] = pd.to_datetime(merged["timestamp"]).dt.date

    def _pos_ratio(s: pd.Series) -> float:
        return float((s > 0.2).mean())

    def _neg_ratio(s: pd.Series) -> float:
        return float((s < -0.2).mean())

    grouped = merged.groupby("date")["sentiment_score"].agg(
        mean_sentiment="mean", sentiment_volatility="std", news_volume="count",
    )
    grouped["positive_ratio"] = merged.groupby("date")["sentiment_score"].apply(_pos_ratio)
    grouped["negative_ratio"] = merged.groupby("date")["sentiment_score"].apply(_neg_ratio)
    return grouped.reset_index()


def sentiment_by_entity(sentiment_long_df: pd.DataFrame, news_df: pd.DataFrame,
                         entity_col: str = "matched_company_id",
                         sentiment_model: str = "vader") -> pd.DataFrame:
    scored = sentiment_long_df[sentiment_long_df["sentiment_model"] == sentiment_model]
    merged = scored.merge(news_df[["news_id", entity_col]], on="news_id", how="left")
    merged = merged[merged[entity_col].notna()]
    return merged.groupby(entity_col)["sentiment_score"].agg(
        mean_sentiment="mean", n_articles="count", std_sentiment="std",
    ).reset_index().sort_values("n_articles", ascending=False)


def label_distribution(sentiment_long_df: pd.DataFrame, sentiment_model: str = "vader") -> pd.Series:
    scored = sentiment_long_df[sentiment_long_df["sentiment_model"] == sentiment_model]
    return scored["sentiment_label"].value_counts()
