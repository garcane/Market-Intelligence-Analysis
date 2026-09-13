"""Orchestrates Stage 4: reads fact_news (from Stage 3 ingestion), scores it
with both sentiment models, validates + stores the result, and reports
model agreement. Run as: python -m src.sentiment.run_sentiment
"""
from __future__ import annotations

import json
import logging

from src.config import PROCESSED_DIR, RAW_DIR
from src.ingestion.store import round_trip_matches
from src.ingestion.validate import ValidationResult
from src.sentiment.agreement import compare_models
from src.sentiment.score import score_news

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _validate_sentiment(df) -> ValidationResult:
    issues = []
    if df.empty:
        issues.append("zero rows produced")
    if df["sentiment_score"].isna().any():
        issues.append(f"{df['sentiment_score'].isna().sum()} null sentiment_score(s)")
    out_of_range = ~df["sentiment_score"].between(-1.0, 1.0)
    if out_of_range.any():
        issues.append(f"{out_of_range.sum()} sentiment_score(s) outside [-1, 1]")
    dupes = df.duplicated(subset=["news_id", "sentiment_model"]).sum()
    if dupes:
        issues.append(f"{dupes} duplicate (news_id, sentiment_model) row(s)")
    return ValidationResult("fact_sentiment", len(issues) == 0, issues, len(df))


def main() -> None:
    news_path = RAW_DIR / "news" / "news.parquet"
    if not news_path.exists():
        raise FileNotFoundError(
            f"{news_path} not found — run `python -m src.ingestion.run_ingestion` first"
        )

    import pandas as pd
    news_df = pd.read_parquet(news_path)
    logger.info("scoring %d news rows", len(news_df))

    sentiment_df = score_news(news_df)
    validation = _validate_sentiment(sentiment_df)
    if not validation.passed:
        logger.error("validation failed: %s", validation.issues)
        raise ValueError(f"fact_sentiment validation failed: {validation.issues}")

    out_path = RAW_DIR / "sentiment" / "fact_sentiment.parquet"
    matches, rt_issues = round_trip_matches(sentiment_df, out_path)
    if not matches:
        raise ValueError(f"round-trip mismatch: {rt_issues}")

    agreement = compare_models(sentiment_df)
    logger.info("model agreement: %s", agreement)

    report = {
        "row_count": len(sentiment_df),
        "n_news_scored": sentiment_df["news_id"].nunique(),
        "label_distribution": sentiment_df.groupby(["sentiment_model", "sentiment_label"])
                                           .size().unstack(fill_value=0).to_dict(orient="index"),
        "model_agreement": agreement,
    }
    with open(PROCESSED_DIR / "sentiment_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Stage 4 sentiment report written. n_news_scored=%d", report["n_news_scored"])


if __name__ == "__main__":
    main()
