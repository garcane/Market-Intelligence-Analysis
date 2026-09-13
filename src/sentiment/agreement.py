"""Measures agreement/disagreement between sentiment models, per the target
spec's instruction not to assume one sentiment model is automatically superior.
"""
from __future__ import annotations

import pandas as pd


def compare_models(sentiment_long_df: pd.DataFrame, model_a: str = "vader",
                    model_b: str = "textblob") -> dict:
    """Input: fact_sentiment-shaped long df (news_id, sentiment_model, sentiment_score, sentiment_label).
    Returns agreement statistics between two models scored on the same news_id set.
    """
    wide = sentiment_long_df.pivot(index="news_id", columns="sentiment_model",
                                    values=["sentiment_score", "sentiment_label"])
    scores_a = wide[("sentiment_score", model_a)]
    scores_b = wide[("sentiment_score", model_b)]
    labels_a = wide[("sentiment_label", model_a)]
    labels_b = wide[("sentiment_label", model_b)]

    valid = scores_a.notna() & scores_b.notna()
    scores_a, scores_b = scores_a[valid], scores_b[valid]
    labels_a, labels_b = labels_a[valid], labels_b[valid]

    n = len(scores_a)
    correlation = float(scores_a.corr(scores_b)) if n > 1 else float("nan")
    exact_label_agreement = float((labels_a == labels_b).mean()) if n else float("nan")

    def _polarity(label: str) -> str:
        if label in ("Bullish", "Slightly Bullish"):
            return "positive"
        if label in ("Bearish", "Slightly Bearish"):
            return "negative"
        return "neutral"

    direction_agreement = float((labels_a.map(_polarity) == labels_b.map(_polarity)).mean()) if n else float("nan")

    return {
        "n_compared": n,
        "pearson_correlation": correlation,
        "exact_label_agreement_rate": exact_label_agreement,
        "direction_agreement_rate": direction_agreement,
        "mean_abs_score_diff": float((scores_a - scores_b).abs().mean()) if n else float("nan"),
    }
