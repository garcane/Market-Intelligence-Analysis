"""Stage 6 orchestrator: loads Stage 3/4 outputs, builds the combined feature
table, validates it, and stores it with round-trip verification.
Run as: python -m src.features.run_features
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from src.config import PROCESSED_DIR, RAW_DIR
from src.features.pipeline import build_all_features
from src.features.target import MODELING_MARKET_IDS
from src.features.validate import validate_features
from src.ingestion.store import round_trip_matches

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def load_market_prices(market_ids: tuple[str, ...] = MODELING_MARKET_IDS) -> dict[str, pd.DataFrame]:
    """Restricted to the explicit modeling universe, not everything in
    data/raw/market_prices/ — that directory also holds Stage 12's index-
    analysis equities and benchmark series, which have no classification
    target and shouldn't flow into the modeling pipeline. See
    src/features/target.py::MODELING_MARKET_IDS.
    """
    market_dir = RAW_DIR / "market_prices"
    result = {}
    for market_id in market_ids:
        path = market_dir / f"{market_id}.parquet"
        if path.exists():
            result[market_id] = pd.read_parquet(path)
        else:
            logger.warning("modeling asset %s has no ingested price data — skipping", market_id)
    return result


def main() -> None:
    market_prices = load_market_prices()
    if not market_prices:
        raise FileNotFoundError("no market data found — run src.ingestion.run_ingestion first")

    sentiment_path = RAW_DIR / "sentiment" / "fact_sentiment.parquet"
    news_path = RAW_DIR / "news" / "news.parquet"
    sentiment_df = pd.read_parquet(sentiment_path) if sentiment_path.exists() else None
    news_df = pd.read_parquet(news_path) if news_path.exists() else None
    if sentiment_df is None:
        logger.warning("no sentiment data found — building market + cross-sectional features only "
                        "(run src.sentiment.run_sentiment first for sentiment features)")

    features = build_all_features(market_prices, sentiment_df, news_df)
    logger.info("built %d feature rows across %d assets", len(features), features["market_id"].nunique())

    validation = validate_features(features)
    if not validation.passed:
        logger.error("validation failed: %s", validation.issues)
        raise ValueError(f"feature validation failed: {validation.issues}")

    out_path = PROCESSED_DIR / "features" / "features.parquet"
    matches, rt_issues = round_trip_matches(features, out_path)
    if not matches:
        raise ValueError(f"round-trip mismatch: {rt_issues}")

    report = {
        "row_count": len(features),
        "n_assets": int(features["market_id"].nunique()),
        "n_feature_columns": len(features.columns) - 2,  # exclude market_id, date
        "columns": [c for c in features.columns if c not in ("market_id", "date")],
        "has_sentiment_features": sentiment_df is not None,
        "assets": sorted(features["market_id"].unique().tolist()),
    }
    with open(PROCESSED_DIR / "features_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Stage 6 feature report written: %d rows, %d columns, assets=%s",
                report["row_count"], report["n_feature_columns"], report["assets"])


if __name__ == "__main__":
    main()
