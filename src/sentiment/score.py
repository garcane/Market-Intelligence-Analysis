"""Dual sentiment scoring (VADER + TextBlob) producing a fact_sentiment-shaped
long table (one row per news_id x sentiment_model), per DATA_MODEL.md §3.3.

Threshold fix: the original repo's category thresholds
(PROJECT_AUDIT.md §3c) had a gap — a documented "Slightly Bullish" band of
0.2 < score < 0.4 silently left [0.4, 0.5) unclassified as Neutral. The
scheme below is a symmetric, gapless partition of [-1, 1].
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from src.sentiment.text_clean import clean_headline

_vader = SentimentIntensityAnalyzer()

# Symmetric, gapless thresholds on a [-1, 1] scale.
LABEL_THRESHOLDS = [
    (0.5, "Bullish"),
    (0.2, "Slightly Bullish"),
    (-0.2, "Neutral"),
    (-0.5, "Slightly Bearish"),
    (float("-inf"), "Bearish"),
]


def label_from_score(score: float) -> str:
    for threshold, label in LABEL_THRESHOLDS:
        if score >= threshold:
            return label
    return "Bearish"  # unreachable given -inf sentinel above; kept for clarity


def score_vader(text: str) -> float:
    return _vader.polarity_scores(text)["compound"]


def score_textblob(text: str) -> float:
    return TextBlob(text).sentiment.polarity


def score_news(news_df: pd.DataFrame, dedupe_on_cleaned_title: bool = True) -> pd.DataFrame:
    """Input: fact_news-shaped df with at least [news_id, title].
    Output: fact_sentiment-shaped long df: news_id, sentiment_model,
    sentiment_score, sentiment_label, scored_at.
    """
    df = news_df.copy()
    df["clean_title"] = df["title"].apply(clean_headline)
    df = df[df["clean_title"] != ""]

    if dedupe_on_cleaned_title:
        before = len(df)
        df = df.drop_duplicates(subset=["clean_title"])
        dropped = before - len(df)
        if dropped:
            import logging
            logging.getLogger(__name__).info("dropped %d exact-duplicate cleaned headline(s)", dropped)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    rows = []
    for _, row in df.iterrows():
        text = row["clean_title"]
        vader_score = score_vader(text)
        tb_score = score_textblob(text)
        rows.append({
            "news_id": row["news_id"], "sentiment_model": "vader",
            "sentiment_score": vader_score, "sentiment_label": label_from_score(vader_score),
            "scored_at": now,
        })
        rows.append({
            "news_id": row["news_id"], "sentiment_model": "textblob",
            "sentiment_score": tb_score, "sentiment_label": label_from_score(tb_score),
            "scored_at": now,
        })
    return pd.DataFrame(rows, columns=[
        "news_id", "sentiment_model", "sentiment_score", "sentiment_label", "scored_at",
    ])
