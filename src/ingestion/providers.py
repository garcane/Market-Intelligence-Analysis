"""Provider adapters. Provider-specific API details stay behind these boundaries."""
from __future__ import annotations

import datetime as dt
from typing import Any

import pandas as pd
import requests

from src.ingestion.base import MarketDataProvider, NewsDataProvider, ProviderError, add_provenance, stable_record_id, with_retries
from src.ingestion.standardize import standardize_market, standardize_news
from src.ingestion.market_data import fetch_market_prices
from src.ingestion.news_data import fetch_headlines


class YahooFinanceProvider(MarketDataProvider):
    name = "yahoo_finance"

    def fetch_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        return standardize_market(fetch_market_prices(symbol, start, end), asset_id=symbol, source=self.name)


class CoinCodexProvider(MarketDataProvider):
    name = "coincodex"
    base_url = "https://coincodex.com/api/coincodex/get_coin_history"

    def __init__(self, timeout: int = 60, chunk_years: int = 2):
        self.timeout = timeout
        self.chunk_years = chunk_years

    def _fetch_chunk(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        n_days = (pd.Timestamp(end) - pd.Timestamp(start)).days + 1
        url = f"{self.base_url}/{symbol}/{start}/{end}/{n_days}"
        def request() -> Any:
            response = requests.get(url, timeout=self.timeout, headers={"User-Agent": "AI-Market-Intelligence/1.0"})
            response.raise_for_status()
            return response.json()
        payload = with_retries(request, provider=self.name)
        rows = payload.get(symbol)
        if not rows:
            raise ProviderError(f"{self.name}: no history returned for {symbol}")
        df = pd.DataFrame(rows, columns=["ts", "close", "volume", "market_cap"])
        df["date"] = pd.to_datetime(df["ts"], unit="s")
        df["source_record_id"] = [stable_record_id(symbol, x) for x in df["ts"]]
        return df[["date", "close", "volume", "market_cap", "source_record_id"]]

    def fetch_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        parts = []
        current = pd.Timestamp(start)
        finish = pd.Timestamp(end)
        while current <= finish:
            chunk_end = min(current + pd.DateOffset(years=self.chunk_years) - pd.Timedelta(days=1), finish)
            parts.append(self._fetch_chunk(symbol, current.date().isoformat(), chunk_end.date().isoformat()))
            current = chunk_end + pd.Timedelta(days=1)
        df = pd.concat(parts, ignore_index=True)
        df["date"] = df["date"].dt.normalize()
        df = df.sort_values("date").drop_duplicates("date", keep="last")
        return standardize_market(df, asset_id=symbol, source=self.name)


class GoogleNewsProvider(NewsDataProvider):
    name = "google_news"

    def fetch_news(self, query: str, max_results: int = 30) -> pd.DataFrame:
        return standardize_news(fetch_headlines(query, max_results=max_results), source=self.name)


class MarketauxProvider(NewsDataProvider):
    """Optional Marketaux adapter. It activates only when MARKETaux_API_TOKEN is configured."""
    name = "marketaux"
    url = "https://api.marketaux.com/v1/news/all"

    def __init__(self, api_token: str | None = None, timeout: int = 30):
        import os
        self.api_token = api_token or os.getenv("MARKETAUX_API_TOKEN")
        self.timeout = timeout

    def fetch_news(self, query: str, max_results: int = 30) -> pd.DataFrame:
        if not self.api_token:
            raise ProviderError("marketaux: MARKETAUX_API_TOKEN is not configured")
        params = {"api_token": self.api_token, "search": query, "language": "en", "limit": min(max_results, 100)}
        def request() -> Any:
            response = requests.get(self.url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        payload = with_retries(request, provider=self.name)
        rows = []
        for item in payload.get("data", []):
            rows.append({
                "article_id": item.get("uuid") or stable_record_id(item.get("url"), item.get("published_at")),
                "published_at": item.get("published_at"),
                "source": self.name,
                "publisher": item.get("source"),
                "title": item.get("title"),
                "description": item.get("description"),
                "url": item.get("url"),
                "entity": query,
                "language": item.get("language", "en"),
            })
        return standardize_news(pd.DataFrame(rows), source=self.name)
