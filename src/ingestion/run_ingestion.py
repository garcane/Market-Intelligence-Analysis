"""Orchestrates the ingestion agentic loop for market prices and news:
Fetch -> Validate -> Store -> Reload -> Compare -> Pass/Fail, with a report
written for inspection. Run as:  python -m src.ingestion.run_ingestion
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import date

from src.config import PROCESSED_DIR
from src.ingestion.market_data import FetchError as MarketFetchError
from src.ingestion.market_data import fetch_market_prices
from src.ingestion.news_data import FetchError as NewsFetchError
from src.ingestion.news_data import fetch_headlines, match_entities
from src.ingestion.store import market_prices_path, news_path, round_trip_matches
from src.ingestion.universe import build_market_universe, load_companies
from src.ingestion.validate import validate_market_prices, validate_news

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def ingest_market_universe(start: str, end: str, market_ids: list[str] | None = None) -> dict:
    universe = build_market_universe()
    if market_ids:
        universe = universe[universe["market_id"].isin(market_ids)]

    report = {"start": start, "end": end, "results": []}
    for _, row in universe.iterrows():
        market_id, symbol = row["market_id"], row["symbol"]
        entry = {"market_id": market_id, "symbol": symbol, "status": "UNKNOWN", "issues": []}
        try:
            df = fetch_market_prices(symbol, start, end)
        except MarketFetchError as exc:
            entry["status"] = "FETCH_FAILED"
            entry["issues"].append(str(exc))
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
        logger.info("PASS %s (%s rows)", market_id, validation.row_count)

    n_pass = sum(1 for r in report["results"] if r["status"] == "PASS")
    report["summary"] = {"total": len(report["results"]), "passed": n_pass,
                          "failed": len(report["results"]) - n_pass}
    return report


def ingest_news(max_results_per_query: int = 20, companies_limit: int | None = None) -> dict:
    companies = load_companies()
    if companies_limit:
        companies = companies.head(companies_limit)

    all_frames = []
    report = {"queries": [], "issues": []}
    for _, row in companies.iterrows():
        query = row["company_name"]
        try:
            df = fetch_headlines(query, max_results=max_results_per_query)
            report["queries"].append({"query": query, "rows": len(df), "status": "FETCHED"})
            if not df.empty:
                all_frames.append(df)
        except NewsFetchError as exc:
            report["queries"].append({"query": query, "rows": 0, "status": "FETCH_FAILED"})
            report["issues"].append(f"{query}: {exc}")

    if not all_frames:
        report["status"] = "NO_DATA"
        return report

    import pandas as pd
    combined = pd.concat(all_frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["url"])
    combined = match_entities(combined)

    validation = validate_news(combined)
    report["row_count"] = validation.row_count
    if not validation.passed:
        report["status"] = "VALIDATION_FAILED"
        report["issues"].extend(validation.issues)
        return report

    store_df = combined.drop(columns=["query"])
    matches, rt_issues = round_trip_matches(store_df, news_path())
    if not matches:
        report["status"] = "ROUND_TRIP_FAILED"
        report["issues"].extend(rt_issues)
        return report

    report["status"] = "PASS"
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
