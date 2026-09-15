"""Provider orchestration with fallback, provenance and health reporting."""
from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter

import pandas as pd

from src.ingestion.base import MarketDataProvider, NewsDataProvider
from src.ingestion.providers import CoinCodexProvider, GoogleNewsProvider, YahooFinanceProvider


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


def default_market_providers() -> list[MarketDataProvider]:
    return [YahooFinanceProvider(), CoinCodexProvider()]


def default_news_providers() -> list[NewsDataProvider]:
    return [GoogleNewsProvider()]
