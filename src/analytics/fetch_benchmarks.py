"""Fetches the benchmark and thematic fund series (S&P 500, Nasdaq-100,
Vanguard FTSE All-World / Emerging Markets, SOXX and the energy ETFs) listed
in data/reference/funds.csv. They are part of the main universe, so the full
ingestion run fetches them too; this is a shortcut for refreshing only them.
Run as: python -m src.analytics.fetch_benchmarks
"""
from __future__ import annotations

import logging
from datetime import date

from src.ingestion.run_ingestion import ingest_market_universe
from src.ingestion.universe import load_funds

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main(start: str = "2023-01-01") -> None:
    report = ingest_market_universe(start, date.today().isoformat(), market_ids=load_funds()["ticker"].tolist())
    failed = [r for r in report["results"] if r["status"] != "PASS"]
    if failed:
        raise ValueError(f"benchmark ingestion failed: {failed}")
    logger.info("benchmarks: %s", report["summary"])


if __name__ == "__main__":
    main()
