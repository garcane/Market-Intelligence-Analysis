"""Provider orchestration with fallback, provenance and health reporting."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from time import perf_counter

import pandas as pd

from src.ingestion.base import HistoricalNewsProvider, MarketDataProvider, NewsDataProvider
from src.ingestion.providers import (
    AlphaVantageNewsProvider,
    CoinCodexProvider,
    FinnhubNewsProvider,
    GoogleNewsProvider,
    MarketauxProvider,
    TiingoProvider,
    YahooFinanceProvider,
)


def fetch_market_with_fallback(providers: list[MarketDataProvider], symbol: str, start: str, end: str) -> tuple[pd.DataFrame, dict]:
    health = {"provider": None, "status": "FAILED", "attempts": []}
    for provider in providers:
        started = perf_counter()
        try:
            df = provider.fetch_prices(symbol, start, end)
            elapsed = round(perf_counter() - started, 3)
            health["attempts"].append({"provider": provider.name, "status": "PASS", "response_time": elapsed, "records": len(df)})
            health.update(provider=provider.name, status="PASS", records_returned=len(df), response_time=elapsed, last_success=datetime.now(timezone.utc).isoformat())
            return df, health
        except Exception as exc:  # noqa: BLE001 - orchestrator must continue to fallback provider
            elapsed = round(perf_counter() - started, 3)
            health["attempts"].append({"provider": provider.name, "status": "FAILED", "response_time": elapsed, "error": str(exc)})
    return pd.DataFrame(), health


def fetch_news_with_fallback(providers: list[NewsDataProvider], query: str, max_results: int = 30) -> tuple[pd.DataFrame, dict]:
    health = {"provider": None, "status": "FAILED", "attempts": []}
    for provider in providers:
        started = perf_counter()
        try:
            df = provider.fetch_news(query, max_results=max_results)
            elapsed = round(perf_counter() - started, 3)
            health["attempts"].append({"provider": provider.name, "status": "PASS", "response_time": elapsed, "records": len(df)})
            health.update(provider=provider.name, status="PASS", records_returned=len(df), response_time=elapsed, last_success=datetime.now(timezone.utc).isoformat())
            return df, health
        except Exception as exc:  # noqa: BLE001 - fallback is deliberate
            elapsed = round(perf_counter() - started, 3)
            health["attempts"].append({"provider": provider.name, "status": "FAILED", "response_time": elapsed, "error": str(exc)})
    return pd.DataFrame(), health


def default_market_providers(asset_type: str | None = None) -> list[MarketDataProvider]:
    # Yahoo Finance first even for crypto: observed to return complete, gap-free
    # daily history for the tracked crypto universe, while CoinCodex was found
    # to silently drop ~11% of days (131 two-day gaps over a ~1,200-day pull) —
    # validate_market_prices doesn't currently check for date-completeness gaps
    # in a 24/7-trading asset, so that regression wasn't caught by validation.
    # CoinCodex stays wired up as a fallback, not the primary source.
    if asset_type == "crypto":
        return [YahooFinanceProvider(), CoinCodexProvider()]
    # Tiingo joins only when its key is set. Alpha Vantage prices are left out:
    # its free plan can't return multi-year history (see AlphaVantageMarketProvider).
    providers: list[MarketDataProvider] = [YahooFinanceProvider()]
    if os.getenv("TIINGO_API_TOKEN"):
        providers.append(TiingoProvider())
    return providers


def default_news_providers() -> list[NewsDataProvider]:
    providers: list[NewsDataProvider] = []
    if os.getenv("MARKETAUX_API_TOKEN"):
        providers.append(MarketauxProvider())
    providers.append(GoogleNewsProvider())
    return providers


def default_historical_news_providers() -> list[HistoricalNewsProvider]:
    """Providers for the news backfill, highest article yield per request first."""
    providers: list[HistoricalNewsProvider] = []
    if os.getenv("FINNHUB_API_KEY"):
        providers.append(FinnhubNewsProvider())
    if os.getenv("ALPHA_VANTAGE_API_KEY"):
        providers.append(AlphaVantageNewsProvider())
    if os.getenv("MARKETAUX_API_TOKEN"):
        providers.append(MarketauxProvider())
    return providers
