"""Orchestrates ingestion through provider adapters:
Fetch -> Validate -> Store -> Reload -> Compare -> Pass/Fail.
Run as: python -m src.ingestion.run_ingestion
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date

from src.config import PROCESSED_DIR
from src.ingestion.base import MarketDataProvider, NewsDataProvider
from src.ingestion.orchestrator import default_market_providers, default_news_providers, fetch_market_with_fallback, fetch_news_with_fallback
from src.ingestion.standardize import merge_news_frames, to_fact_news
from src.ingestion.store import market_prices_path, news_path, round_trip_matches
from src.ingestion.universe import build_market_universe, load_companies
from src.ingestion.validate import validate_market_prices, validate_news
from src.ingestion.news_backfill import collect_recent_news, ingested_market_symbols
from src.ingestion.news_data import match_entities
from src.ingestion.providers import YahooFinanceNewsProvider

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def ingest_market_universe(start: str, end: str, market_ids: list[str] | None = None,
                           providers: list[MarketDataProvider] | None = None) -> dict:
    universe = build_market_universe()
    if market_ids:
        universe = universe[universe["market_id"].isin(market_ids)]

    report = {"start": start, "end": end, "results": [], "provider_health": []}
    for _, row in universe.iterrows():
        market_id, symbol, asset_type = row["market_id"], row["symbol"], row["asset_type"]
        provider_list = providers or default_market_providers(asset_type)
        entry = {"market_id": market_id, "symbol": symbol, "status": "UNKNOWN", "issues": []}
        df, health = fetch_market_with_fallback(provider_list, symbol, start, end)
        report["provider_health"].append({"market_id": market_id, "asset_type": asset_type, **health})
        if df.empty:
            entry["status"] = "FETCH_FAILED"
            entry["issues"].extend(a.get("error", "provider failed") for a in health["attempts"] if a["status"] == "FAILED")
            report["results"].append(entry)
            continue

        validation = validate_market_prices(df, market_id)
        entry["row_count"] = validation.row_count
        if not validation.passed:
            entry["status"] = "VALIDATION_FAILED"
            entry["issues"].extend(validation.issues)
            report["results"].append(entry)
            continue

        matches, rt_issues = round_trip_matches(df, market_prices_path(market_id))
        if not matches:
            entry["status"] = "ROUND_TRIP_FAILED"
            entry["issues"].extend(rt_issues)
            report["results"].append(entry)
            continue

        entry["status"] = "PASS"
        report["results"].append(entry)
        logger.info("PASS %s via %s (%s rows)", market_id, health["provider"], validation.row_count)

    n_pass = sum(1 for r in report["results"] if r["status"] == "PASS")
    report["summary"] = {"total": len(report["results"]), "passed": n_pass,
                          "failed": len(report["results"]) - n_pass}
    return report


def ingest_news(max_results_per_query: int = 20, companies_limit: int | None = None,
                providers: list[NewsDataProvider] | None = None,
                ticker_news: NewsDataProvider | None | bool = True) -> dict:
    """Keyword news per company (Google News) plus the latest news for every
    ingested ticker (Yahoo Finance). Pass ticker_news=False to skip the latter."""
    companies = load_companies()
    if companies_limit:
        companies = companies.head(companies_limit)

    provider_list = providers or default_news_providers()
    all_frames = []
    report = {"queries": [], "issues": [], "provider_health": []}
    for _, row in companies.iterrows():
        query = row["company_name"]
        df, health = fetch_news_with_fallback(provider_list, query, max_results=max_results_per_query)
        report["provider_health"].append({"query": query, **health})
        if health["status"] != "PASS":
            report["queries"].append({"query": query, "rows": 0, "status": "FETCH_FAILED"})
            report["issues"].append(f"{query}: all news providers failed")
            continue
        report["queries"].append({"query": query, "rows": len(df), "status": "FETCHED", "provider": health["provider"]})
        if not df.empty:
            all_frames.append(df.assign(query=query))

    import pandas as pd

    fact_frames = []
    if all_frames:
        keyword = pd.concat(all_frames, ignore_index=True).drop_duplicates(subset=["url"])
        fact_frames.append(match_entities(to_fact_news(keyword.drop(columns=["query"]))))
    if ticker_news is not False:
        provider = ticker_news if isinstance(ticker_news, NewsDataProvider) else YahooFinanceNewsProvider()
        symbols, entity_by_market = ingested_market_symbols()
        recent, report["ticker_news"] = collect_recent_news(provider, symbols, entity_by_market)
        if not recent.empty:
            fact_frames.append(recent)

    if not fact_frames:
        report["status"] = "NO_DATA"
        return report

    # ticker-attributed rows first: on a shared url they are the more precise match
    combined = pd.concat(fact_frames[::-1], ignore_index=True).drop_duplicates(subset=["url"])

    validation = validate_news(combined)
    report["row_count"] = validation.row_count
    if not validation.passed:
        report["status"] = "VALIDATION_FAILED"
        report["issues"].extend(validation.issues)
        return report

    # Merge rather than overwrite: news.parquet also holds the historical
    # backfill (src/ingestion/run_news_backfill.py), which a plain write
    # would wipe on the next routine ingestion.
    path = news_path()
    existing = pd.read_parquet(path) if path.exists() else None
    store_df = merge_news_frames(existing, combined)
    matches, rt_issues = round_trip_matches(store_df, path)
    if not matches:
        report["status"] = "ROUND_TRIP_FAILED"
        report["issues"].extend(rt_issues)
        return report

    report["status"] = "PASS"
    report["stored_row_count"] = len(store_df)
    report["matched_company_rate"] = float(combined["matched_company_id"].notna().mean())
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default=date.today().isoformat())
    parser.add_argument("--assets", default=None, help="comma-separated market_ids; default = full universe")
    parser.add_argument("--skip-news", action="store_true")
    parser.add_argument("--news-companies-limit", type=int, default=5)
    args = parser.parse_args()

    market_ids = args.assets.split(",") if args.assets else None
    market_report = ingest_market_universe(args.start, args.end, market_ids)
    with open(PROCESSED_DIR / "ingestion_report_market.json", "w", encoding="utf-8") as f:
        json.dump(market_report, f, indent=2, default=str)
    logger.info("Market ingestion summary: %s", market_report["summary"])

    if not args.skip_news:
        news_report = ingest_news(companies_limit=args.news_companies_limit)
        with open(PROCESSED_DIR / "ingestion_report_news.json", "w", encoding="utf-8") as f:
            json.dump(news_report, f, indent=2, default=str)
        logger.info("News ingestion status: %s", news_report.get("status"))


if __name__ == "__main__":
    main()
