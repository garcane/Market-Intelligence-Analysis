"""Provider adapters. Provider-specific API details stay behind these boundaries.

Keyed providers read their key from the environment (`.env`, see
`.env.example`) and are only added to the default chains in
`orchestrator.py` when that key is set, so key-free runs behave as before.
"""
from __future__ import annotations

import os
import re
from typing import Any

import pandas as pd
import requests

from src.ingestion.base import (
    AccessDenied,
    HistoricalNewsProvider,
    MarketDataProvider,
    NewsDataProvider,
    ProviderError,
    QuotaExhausted,
    redact,
    stable_record_id,
    with_retries,
)
from src.ingestion.market_data import fetch_market_prices
from src.ingestion.news_data import fetch_headlines
from src.ingestion.standardize import standardize_market, standardize_news

USER_AGENT = {"User-Agent": "AI-Market-Intelligence/1.0"}
PRICE_COLUMNS = ["open", "high", "low", "close"]


def get_json(url: str, *, provider: str, params: dict | None = None, headers: dict | None = None,
             timeout: int = 30, secrets: tuple[str | None, ...] = ()) -> Any:
    """GET a JSON endpoint with retries. Maps quota and access failures to
    non-retryable errors and redacts `secrets` from every error message."""
    def request() -> Any:
        try:
            response = requests.get(url, params=params, headers={**USER_AGENT, **(headers or {})},
                                    timeout=timeout)
        except requests.RequestException as exc:
            # `from None`: the chained exception's message contains the full URL.
            raise ProviderError(redact(f"{provider}: request failed: {exc}", *secrets)) from None
        body = redact(response.text[:200], *secrets)
        if response.status_code in (402, 429):
            raise QuotaExhausted(f"{provider}: HTTP {response.status_code}: {body}")
        if response.status_code in (401, 403):
            raise AccessDenied(f"{provider}: HTTP {response.status_code}: {body}")
        if response.status_code >= 400:
            raise ProviderError(f"{provider}: HTTP {response.status_code}: {body}")
        try:
            return response.json()
        except ValueError:
            raise ProviderError(f"{provider}: response was not JSON: {body}") from None

    return with_retries(request, provider=provider)


def _require_key(value: str | None, provider: str, env_var: str) -> str:
    if not value:
        raise AccessDenied(f"{provider}: {env_var} is not set")
    return value


# --- Market data --------------------------------------------------------------------

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
            response = requests.get(url, timeout=self.timeout, headers=USER_AGENT)
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
        # CoinCodex's API expects a bare symbol (e.g. "BTC"); the universe
        # passes Yahoo-style crypto symbols (e.g. "BTC-USD") since that's the
        # convention yfinance needs — strip the suffix for this provider only.
        symbol = symbol.removesuffix("-USD")
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


class TiingoProvider(MarketDataProvider):
    """Equity end-of-day prices (free plan: 30+ years of history, personal use only)."""
    name = "tiingo"
    base_url = "https://api.tiingo.com/tiingo/daily"

    def __init__(self, api_token: str | None = None, timeout: int = 30):
        self.api_token = api_token or os.getenv("TIINGO_API_TOKEN")
        self.timeout = timeout

    def fetch_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        token = _require_key(self.api_token, self.name, "TIINGO_API_TOKEN")
        payload = get_json(f"{self.base_url}/{symbol}/prices", provider=self.name,
                           params={"startDate": start, "endDate": end, "format": "json"},
                           headers={"Authorization": f"Token {token}"},
                           timeout=self.timeout, secrets=(token,))
        return self.parse_prices(payload, symbol)

    @staticmethod
    def parse_prices(payload: Any, symbol: str) -> pd.DataFrame:
        if not isinstance(payload, list) or not payload:
            raise ProviderError(f"tiingo: no price history returned for {symbol}")
        df = pd.DataFrame(payload)
        df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None).dt.normalize()
        df = df.sort_values("date").reset_index(drop=True)
        # Tiingo's OHLCV is raw; Yahoo's, used everywhere else, is split-adjusted.
        # Divide each row by the product of the split factors that come after it,
        # or a split (NVDA 10:1, 2024-06-10) reads as a 90% crash. Only splits
        # inside the requested window are seen, so fetch through today.
        split = df["splitFactor"].astype(float).fillna(1.0) if "splitFactor" in df else pd.Series(1.0, index=df.index)
        later_splits = split[::-1].cumprod()[::-1].shift(-1).fillna(1.0)
        for col in PRICE_COLUMNS:
            df[col] = df[col].astype(float) / later_splits
        df["volume"] = df["volume"].astype(float) * later_splits
        df["adj_close"] = df["adjClose"].astype(float) if "adjClose" in df else float("nan")
        df["source_record_id"] = [stable_record_id("tiingo", symbol, d) for d in df["date"]]
        df = df[["date", *PRICE_COLUMNS, "adj_close", "volume", "source_record_id"]]
        return standardize_market(df, asset_id=symbol, source="tiingo")


AV_KEY_ECHO = re.compile(r"(api ?key (?:as|is|=)?\s*)[A-Z0-9]{8,}", re.IGNORECASE)


def check_alpha_vantage_payload(payload: Any, api_key: str | None = None) -> None:
    """Alpha Vantage reports errors, quota and premium-only endpoints inside an
    HTTP 200 body, so they have to be detected from the JSON. Its quota message
    echoes the caller's API key, so every message is redacted before raising."""
    if not isinstance(payload, dict):
        raise ProviderError("alpha_vantage: unexpected response shape")

    def clean(text: str) -> str:
        return AV_KEY_ECHO.sub(r"\1***", redact(text, api_key))[:200]

    if "Error Message" in payload:
        raise ProviderError(f"alpha_vantage: {clean(str(payload['Error Message']))}")
    has_data = "feed" in payload or any(k.startswith("Time Series") for k in payload)
    for key in ("Note", "Information"):
        message = str(payload.get(key) or "")
        if not message or has_data:
            continue
        lower = message.lower()
        # The daily-quota message also says "subscribe to any of the premium
        # plans", so quota phrases must be checked before "premium".
        if any(p in lower for p in ("rate limit", "requests per day", "call frequency")):
            raise QuotaExhausted(f"alpha_vantage: {clean(message)}")
        if "premium" in lower:
            raise AccessDenied(f"alpha_vantage: {clean(message)}")
        if "apikey" in lower and ("invalid" in lower or "missing" in lower):
            raise AccessDenied(f"alpha_vantage: {clean(message)}")
        if "no articles" in lower:
            return
        raise ProviderError(f"alpha_vantage: {clean(message)}")


class AlphaVantageMarketProvider(MarketDataProvider):
    """Equity prices from TIME_SERIES_DAILY (raw, unadjusted).

    Not in the default fallback chain. Probed 2026-09-26: outputsize=full is
    premium, and compact returns only ~100 trading days, which the truncation
    guard below refuses for any multi-year request. Usable with a paid plan,
    or for short recent windows."""
    name = "alpha_vantage"
    url = "https://www.alphavantage.co/query"
    MAX_START_GAP_DAYS = 10

    def __init__(self, api_key: str | None = None, outputsize: str = "full", timeout: int = 30):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        self.outputsize = outputsize
        self.timeout = timeout

    def fetch_prices(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        key = _require_key(self.api_key, self.name, "ALPHA_VANTAGE_API_KEY")
        payload = get_json(self.url, provider=self.name, timeout=self.timeout, secrets=(key,),
                           params={"function": "TIME_SERIES_DAILY", "symbol": symbol,
                                   "outputsize": self.outputsize, "apikey": key})
        check_alpha_vantage_payload(payload, key)
        return self.parse_prices(payload, symbol, start, end)

    @classmethod
    def parse_prices(cls, payload: Any, symbol: str, start: str, end: str) -> pd.DataFrame:
        check_alpha_vantage_payload(payload)
        series = payload.get("Time Series (Daily)")
        if not series:
            raise ProviderError(f"alpha_vantage: no price history returned for {symbol}")
        df = pd.DataFrame.from_dict(series, orient="index").rename(columns={
            "1. open": "open", "2. high": "high", "3. low": "low", "4. close": "close", "5. volume": "volume"})
        df.index = pd.to_datetime(df.index)
        df = df.rename_axis("date").reset_index().sort_values("date")
        df = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))].reset_index(drop=True)
        if df.empty:
            raise ProviderError(f"alpha_vantage: no rows for {symbol} between {start} and {end}")
        # Refuse truncated or unadjusted history rather than hand the chain a
        # series that would overwrite a full, split-adjusted one.
        gap_days = (df["date"].iloc[0] - pd.Timestamp(start)).days
        if gap_days > cls.MAX_START_GAP_DAYS:
            raise ProviderError(f"alpha_vantage: history for {symbol} starts {df['date'].iloc[0].date()}, "
                                f"{gap_days} days after the requested {start} (outputsize limit?)")
        close = df["close"].astype(float)
        jump = close / close.shift(1)
        if ((jump < 0.5) | (jump > 2.0)).any():
            raise ProviderError(f"alpha_vantage: {symbol} has a split-sized one-day jump in unadjusted prices")
        df["adj_close"] = float("nan")
        df["source_record_id"] = [stable_record_id("alpha_vantage", symbol, d) for d in df["date"]]
        return standardize_market(df, asset_id=symbol, source="alpha_vantage")


# --- News --------------------------------------------------------------------------------

class GoogleNewsProvider(NewsDataProvider):
    name = "google_news"

    def fetch_news(self, query: str, max_results: int = 30) -> pd.DataFrame:
        return standardize_news(fetch_headlines(query, max_results=max_results), source=self.name)


def _nested_url(value: Any) -> str | None:
    return value.get("url") if isinstance(value, dict) else None


class YahooFinanceNewsProvider(NewsDataProvider):
    """Latest news for a Yahoo Finance symbol (e.g. NVDA, BTC-USD) via yfinance.
    Keyless. There is no date-range query: each call returns the most recent
    ~100 stories (probed 2026-09-26: 1 to 12 days back), so history builds
    up by collecting daily rather than by backfilling."""
    name = "yahoo_finance_news"

    def __init__(self, count: int = 100):
        self.count = count

    def fetch_news(self, query: str, max_results: int | None = None) -> pd.DataFrame:
        import yfinance as yf

        try:
            items = yf.Ticker(query).get_news(count=max_results or self.count, tab="news")
        except Exception as exc:  # noqa: BLE001 - yfinance raises assorted network/parse errors
            raise ProviderError(f"{self.name}: {query}: {type(exc).__name__}: {exc}") from None
        return self.parse_items(items or [], entity=query)

    @staticmethod
    def parse_items(items: list, entity: str | None) -> pd.DataFrame:
        rows = []
        for item in items:
            content = item.get("content") if isinstance(item, dict) else None
            if not isinstance(content, dict):
                continue
            url = _nested_url(content.get("canonicalUrl")) or _nested_url(content.get("clickThroughUrl"))
            if not content.get("title") or not url or not content.get("pubDate"):
                continue
            provider = content.get("provider") if isinstance(content.get("provider"), dict) else {}
            rows.append({
                "article_id": content.get("id") or item.get("id") or stable_record_id(url, content.get("pubDate")),
                "published_at": content.get("pubDate"),
                "source": "yahoo_finance_news",
                "publisher": provider.get("displayName"),
                "title": content.get("title"),
                "description": content.get("summary") or content.get("description") or None,
                "url": url,
                "entity": entity,
                "language": "en",
            })
        return standardize_news(pd.DataFrame(rows), source="yahoo_finance_news")


class FinnhubNewsProvider(HistoricalNewsProvider):
    """Company news by date range. North American equities only; free plan is
    rate-limited to 60 calls/minute.

    Probed 2026-09-26: responses cap at ~250 articles (a 7-day NVDA window came
    back with only its last 3 days), hence 1-day windows. Nothing older than
    about a year is returned, hence the history limit."""
    name = "finnhub"
    url = "https://finnhub.io/api/v1/company-news"
    window_days = 1
    daily_request_budget = None
    history_limit_days = 365
    min_interval_seconds = 1.1

    def __init__(self, api_key: str | None = None, timeout: int = 30):
        self.api_key = api_key or os.getenv("FINNHUB_API_KEY")
        self.timeout = timeout

    def provider_symbol(self, market_id: str, asset_type: str) -> str | None:
        return market_id if asset_type == "equity" else None

    def fetch_window_raw(self, symbol: str, start: str, end: str) -> Any:
        key = _require_key(self.api_key, self.name, "FINNHUB_API_KEY")
        payload = get_json(self.url, provider=self.name, timeout=self.timeout, secrets=(key,),
                           params={"symbol": symbol, "from": start, "to": end},
                           headers={"X-Finnhub-Token": key})
        if isinstance(payload, dict) and payload.get("error"):
            raise AccessDenied(f"finnhub: {str(payload['error'])[:200]}")
        if not isinstance(payload, list):
            raise ProviderError("finnhub: unexpected response shape")
        return payload

    @staticmethod
    def parse_window(raw: Any) -> pd.DataFrame:
        rows = [{
            "article_id": str(item.get("id") or stable_record_id(item.get("url"), item.get("datetime"))),
            "published_at": pd.to_datetime(item.get("datetime"), unit="s"),
            "source": "finnhub",
            "publisher": item.get("source"),
            "title": item.get("headline"),
            "description": item.get("summary"),
            "url": item.get("url"),
            "language": "en",
        } for item in (raw or []) if item.get("headline") and item.get("url") and item.get("datetime")]
        return standardize_news(pd.DataFrame(rows), source="finnhub")


class AlphaVantageNewsProvider(HistoricalNewsProvider):
    """NEWS_SENTIMENT by ticker and time window; covers crypto as CRYPTO:<symbol>.
    Free plan: about 25 requests/day."""
    name = "alpha_vantage_news"
    url = "https://www.alphavantage.co/query"
    window_days = 30
    daily_request_budget = 25
    min_interval_seconds = 13.0

    def __init__(self, api_key: str | None = None, timeout: int = 30, limit: int = 1000):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        self.timeout = timeout
        self.limit = limit

    def provider_symbol(self, market_id: str, asset_type: str) -> str | None:
        return market_id if asset_type == "equity" else f"CRYPTO:{market_id}"

    def fetch_window_raw(self, symbol: str, start: str, end: str) -> Any:
        key = _require_key(self.api_key, self.name, "ALPHA_VANTAGE_API_KEY")
        payload = get_json(self.url, provider=self.name, timeout=self.timeout, secrets=(key,), params={
            "function": "NEWS_SENTIMENT", "tickers": symbol, "limit": self.limit, "sort": "LATEST",
            "time_from": pd.Timestamp(start).strftime("%Y%m%dT0000"),
            "time_to": pd.Timestamp(end).strftime("%Y%m%dT2359"),
            "apikey": key})
        check_alpha_vantage_payload(payload, key)
        return payload

    @staticmethod
    def parse_window(raw: Any) -> pd.DataFrame:
        feed = raw.get("feed", []) if isinstance(raw, dict) else []
        rows = [{
            "article_id": stable_record_id(item.get("url"), item.get("time_published")),
            "published_at": pd.to_datetime(item.get("time_published"), format="%Y%m%dT%H%M%S"),
            "source": "alpha_vantage_news",
            "publisher": item.get("source"),
            "title": item.get("title"),
            "description": item.get("summary"),
            "url": item.get("url"),
            "language": "en",
        } for item in feed if item.get("title") and item.get("url") and item.get("time_published")]
        return standardize_news(pd.DataFrame(rows), source="alpha_vantage_news")
