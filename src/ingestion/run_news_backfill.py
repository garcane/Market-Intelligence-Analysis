"""Historical news backfill: fetch uncached windows, merge them into
data/raw/news/news.parquet, and report sentiment coverage by split period.
Safe to run daily; it resumes where it stopped.

Run as: python -m src.ingestion.run_news_backfill [--max-requests N] [--merge-only]
"""
from __future__ import annotations

import argparse
import logging
from datetime import date

import pandas as pd

from src.config import PROCESSED_DIR, RAW_DIR
from src.features.target import MODELING_MARKET_IDS
from src.ingestion.news_backfill import CACHE_ROOT, DEFAULT_EARLIEST, coverage_report, merge_backfill, run_backfill
from src.ingestion.orchestrator import default_historical_news_providers
from src.ingestion.providers_health import write_health_report
from src.ingestion.standardize import merge_news_frames
from src.ingestion.store import news_path, round_trip_matches
from src.ingestion.universe import build_market_universe, entity_to_market_map
from src.ingestion.validate import validate_news
from src.models.split import DEFAULT_TRAIN_END, DEFAULT_VAL_END

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Ablation re-run gate (plan Step 5): share of training-period asset-days with news.
TRAINING_COVERAGE_GATE = 0.25


def modelling_markets() -> tuple[list[tuple[str, str]], dict[str, tuple[str, str]]]:
    universe = build_market_universe()
    universe = universe[universe["market_id"].isin(MODELING_MARKET_IDS)]
    markets = list(zip(universe["market_id"], universe["asset_type"]))
    market_to_entity = {m: e for e, m in entity_to_market_map().items()}
    entity_by_market = {m: (market_to_entity[m], t) for m, t in markets if m in market_to_entity}
    return markets, entity_by_market


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-requests", type=int, default=None, help="cap on network calls this run")
    parser.add_argument("--earliest", default=DEFAULT_EARLIEST.isoformat())
    parser.add_argument("--providers", default=None, help="comma-separated subset, e.g. finnhub,marketaux")
    parser.add_argument("--merge-only", action="store_true", help="re-parse the cache without fetching")
    args = parser.parse_args()

    markets, entity_by_market = modelling_markets()
    report: dict = {"run_date": date.today().isoformat()}

    if not args.merge_only:
        providers = default_historical_news_providers()
        if args.providers:
            wanted = set(args.providers.split(","))
            providers = [p for p in providers if p.name in wanted]
        if not providers:
            logger.warning("no historical news provider has a key set — see .env.example; merging cache only")
        report["fetch"] = run_backfill(providers, markets, earliest=date.fromisoformat(args.earliest),
                                       max_requests=args.max_requests)

    backfill = merge_backfill(CACHE_ROOT, entity_by_market)
    path = news_path()
    existing = pd.read_parquet(path) if path.exists() else None
    before = 0 if existing is None else len(existing)
    if backfill.empty:
        merged = existing if existing is not None else pd.DataFrame()
    else:
        merged = merge_news_frames(existing, backfill)
        validation = validate_news(merged)
        if not validation.passed:
            raise ValueError(f"merged news failed validation: {validation.issues}")
        matches, issues = round_trip_matches(merged, path)
        if not matches:
            raise ValueError(f"news round-trip failed: {issues}")
    report["news_rows"] = {"before": before, "after": len(merged), "backfill_parsed": len(backfill)}

    trading_dates = {}
    for market_id, _ in markets:
        price_path = RAW_DIR / "market_prices" / f"{market_id}.parquet"
        if price_path.exists():
            trading_dates[market_id] = pd.read_parquet(price_path, columns=["date"])["date"]
    coverage = coverage_report(merged, trading_dates, entity_by_market, DEFAULT_TRAIN_END, DEFAULT_VAL_END)
    train_pct = coverage["totals"]["train"]["pct"] or 0.0
    coverage["training_gate"] = {"threshold": TRAINING_COVERAGE_GATE, "value": train_pct,
                                 "met": train_pct >= TRAINING_COVERAGE_GATE}
    report["coverage"] = coverage

    write_health_report(coverage, PROCESSED_DIR / "news_coverage.json")
    write_health_report(report, PROCESSED_DIR / "news_backfill_report.json")
    logger.info("news rows %s -> %s; coverage train/validation/test: %s / %s / %s; ablation gate %s",
                before, len(merged), coverage["totals"]["train"]["pct"],
                coverage["totals"]["validation"]["pct"], coverage["totals"]["test"]["pct"],
                "MET" if coverage["training_gate"]["met"] else "not met")


if __name__ == "__main__":
    main()
