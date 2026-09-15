"""Fetches market-index benchmark series (S&P 500, Nasdaq, semiconductor ETF)
for Stage 12 (AI Equity Indices). These aren't companies or crypto assets, so
they sit outside dim_market/the Stage 1 universe — a small standalone script
reusing the same fetch/validate/store primitives as the main ingestion
pipeline, rather than force them into the company/crypto reference tables
they don't belong in.
Run as: python -m src.analytics.fetch_benchmarks
"""
from __future__ import annotations

import logging
from datetime import date

from src.ingestion.market_data import fetch_market_prices
from src.ingestion.store import market_prices_path, round_trip_matches
from src.ingestion.validate import validate_market_prices

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BENCHMARKS = {
    "SPX": "^GSPC",       # S&P 500
    "NASDAQ": "^IXIC",    # Nasdaq Composite
    "SOXX": "SOXX",       # iShares Semiconductor ETF
}


def main(start: str = "2023-06-01") -> None:
    for market_id, symbol in BENCHMARKS.items():
        df = fetch_market_prices(symbol, start, date.today().isoformat())
        validation = validate_market_prices(df, market_id)
        if not validation.passed:
            raise ValueError(f"{market_id}: {validation.issues}")
        matches, issues = round_trip_matches(df, market_prices_path(market_id))
        if not matches:
            raise ValueError(f"{market_id}: round-trip failed: {issues}")
        logger.info("PASS %s (%s, %d rows)", market_id, symbol, len(df))


if __name__ == "__main__":
    main()
