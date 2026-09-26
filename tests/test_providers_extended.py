"""Offline tests for the keyed providers. HTTP is stubbed; nothing hits the network."""
import json

import pandas as pd
import pytest
import requests

import src.ingestion.base as base
import src.ingestion.providers as providers
from src.ingestion.base import AccessDenied, ProviderError, QuotaExhausted
from src.ingestion.orchestrator import default_historical_news_providers, default_market_providers
from src.ingestion.providers import (
    AlphaVantageMarketProvider,
    AlphaVantageNewsProvider,
    FinnhubNewsProvider,
    MarketauxProvider,
    TiingoProvider,
)

KEY_VARS = ["MARKETAUX_API_TOKEN", "TIINGO_API_TOKEN", "FINNHUB_API_KEY", "ALPHA_VANTAGE_API_KEY"]
SECRET = "SECRET-TOKEN-123"


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload) if payload is not None else ""

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


@pytest.fixture
def http(monkeypatch):
    """Queue responses; record every requests.get call."""
    calls, queue = [], []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append({"url": url, "params": params or {}, "headers": headers or {}})
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(providers.requests, "get", fake_get)
    monkeypatch.setattr(base.time, "sleep", lambda s: None)
    return calls, queue


# --- Tiingo ------------------------------------------------------------------------

def _tiingo_rows():
    # 10:1 split on day 3: raw prices before it are 10x higher.
    return [
        {"date": "2024-06-06T00:00:00.000Z", "open": 1200, "high": 1250, "low": 1190, "close": 1210,
         "adjClose": 120.9, "volume": 100, "splitFactor": 1.0},
        {"date": "2024-06-07T00:00:00.000Z", "open": 1205, "high": 1215, "low": 1195, "close": 1200,
         "adjClose": 119.9, "volume": 110, "splitFactor": 1.0},
        {"date": "2024-06-10T00:00:00.000Z", "open": 120, "high": 122, "low": 119, "close": 121,
         "adjClose": 121.0, "volume": 1000, "splitFactor": 10.0},
    ]


def test_tiingo_adjusts_raw_prices_for_splits():
    df = TiingoProvider.parse_prices(_tiingo_rows(), "NVDA")
    assert df["close"].round(4).tolist() == [121.0, 120.0, 121.0]  # no fake 90% crash
    assert df["volume"].tolist() == [1000.0, 1100.0, 1000.0]
    assert df["adj_close"].iloc[0] == pytest.approx(120.9)
    assert df["source"].iloc[0] == "tiingo"
    assert pd.api.types.is_datetime64_any_dtype(df["date"])


def test_tiingo_sends_token_in_header_not_url(http, monkeypatch):
    calls, queue = http
    queue.append(FakeResponse(200, _tiingo_rows()))
    TiingoProvider(api_token=SECRET).fetch_prices("NVDA", "2024-06-01", "2024-06-30")
    assert calls[0]["headers"]["Authorization"] == f"Token {SECRET}"
    assert SECRET not in json.dumps(calls[0]["params"])


def test_rate_limit_is_not_retried(http):
    calls, queue = http
    queue.append(FakeResponse(429, {"detail": "rate limited"}))
    with pytest.raises(QuotaExhausted):
        TiingoProvider(api_token=SECRET).fetch_prices("NVDA", "2024-06-01", "2024-06-30")
    assert len(calls) == 1


def test_missing_key_is_access_denied():
    with pytest.raises(AccessDenied):
        TiingoProvider(api_token="").fetch_prices("NVDA", "2024-06-01", "2024-06-30")


def test_token_redacted_from_network_errors(http):
    calls, queue = http
    queue.append(requests.ConnectionError(f"Max retries exceeded with url: /v1/news/all?api_token={SECRET}"))
    with pytest.raises(ProviderError) as info:
        MarketauxProvider(api_token=SECRET).fetch_window_raw("NVDA", "2024-01-01", "2024-01-07")
    assert SECRET not in str(info.value)
    assert "***" in str(info.value)


# --- Alpha Vantage prices -------------------------------------------------------------

def _av_series(closes: dict) -> dict:
    return {"Meta Data": {}, "Time Series (Daily)": {
        d: {"1. open": c, "2. high": c, "3. low": c, "4. close": c, "5. volume": "10"} for d, c in closes.items()}}


def test_alpha_vantage_parses_and_filters_window():
    payload = _av_series({"2024-01-02": "100", "2024-01-03": "101", "2024-01-04": "102"})
    df = AlphaVantageMarketProvider.parse_prices(payload, "MSFT", "2024-01-03", "2024-01-04")
    assert df["close"].tolist() == [101.0, 102.0]
    assert df["adj_close"].isna().all()


def test_alpha_vantage_refuses_truncated_history():
    payload = _av_series({"2024-05-01": "100", "2024-05-02": "101"})
    with pytest.raises(ProviderError, match="starts 2024-05-01"):
        AlphaVantageMarketProvider.parse_prices(payload, "MSFT", "2023-06-01", "2024-05-02")


def test_alpha_vantage_refuses_unadjusted_split():
    payload = _av_series({"2024-06-06": "1200", "2024-06-07": "1210", "2024-06-10": "121"})
    with pytest.raises(ProviderError, match="split"):
        AlphaVantageMarketProvider.parse_prices(payload, "NVDA", "2024-06-06", "2024-06-10")


@pytest.mark.parametrize("message,error", [
    ("Thank you for using Alpha Vantage! This is a premium endpoint.", AccessDenied),
    ("Our standard API rate limit is 25 requests per day.", QuotaExhausted),
])
def test_alpha_vantage_errors_inside_http_200(http, message, error):
    calls, queue = http
    queue.append(FakeResponse(200, {"Information": message}))
    with pytest.raises(error):
        AlphaVantageMarketProvider(api_key=SECRET).fetch_prices("MSFT", "2024-01-01", "2024-01-31")
    assert len(calls) == 1


# --- News parsers ---------------------------------------------------------------------

def test_finnhub_parse_window():
    raw = [{"id": 7, "datetime": 1704200000, "headline": "Nvidia beats", "source": "Reuters",
            "summary": "s", "url": "https://x/1"},
           {"id": 8, "datetime": 1704200000, "headline": "", "url": "https://x/2"}]  # no headline: dropped
    df = FinnhubNewsProvider.parse_window(raw)
    assert len(df) == 1
    assert df["article_id"].iloc[0] == "7"
    assert df["published_at"].iloc[0] == pd.Timestamp(1704200000, unit="s")
    assert df["source"].iloc[0] == "finnhub"


def test_finnhub_covers_equities_only():
    provider = FinnhubNewsProvider(api_key=SECRET)
    assert provider.provider_symbol("NVDA", "equity") == "NVDA"
    assert provider.provider_symbol("BTC", "crypto") is None


def test_alpha_vantage_news_parse_and_crypto_symbol():
    raw = {"items": "1", "feed": [{"title": "Bitcoin rises", "url": "https://x/3", "source": "CoinDesk",
                                   "summary": "s", "time_published": "20240110T153000"}]}
    df = AlphaVantageNewsProvider.parse_window(raw)
    assert df["published_at"].iloc[0] == pd.Timestamp("2024-01-10 15:30:00")
    assert AlphaVantageNewsProvider(api_key=SECRET).provider_symbol("BTC", "crypto") == "CRYPTO:BTC"


def test_alpha_vantage_news_no_articles_is_empty_not_error(http):
    calls, queue = http
    queue.append(FakeResponse(200, {"Information": "No articles found. Please adjust the time range."}))
    raw = AlphaVantageNewsProvider(api_key=SECRET).fetch_window_raw("NVDA", "2021-01-01", "2021-01-31")
    assert AlphaVantageNewsProvider.parse_window(raw).empty


def test_marketaux_window_query_and_parse(http):
    calls, queue = http
    queue.append(FakeResponse(200, {"data": [{"uuid": "u1", "title": "Nvidia", "url": "https://x/4",
                                              "published_at": "2024-01-31T20:11:00.000000Z", "source": "cnbc.com"}]}))
    provider = MarketauxProvider(api_token=SECRET)
    df = provider.parse_window(provider.fetch_window_raw("NVDA", "2024-01-25", "2024-01-31"))
    params = calls[0]["params"]
    assert params["symbols"] == "NVDA" and params["published_after"] == "2024-01-25"
    assert params["published_before"] == "2024-01-31T23:59:59" and params["limit"] == 3
    assert df["article_id"].iloc[0] == "u1"
    assert df["published_at"].iloc[0].tzinfo is None


def test_marketaux_usage_limit_is_quota(http):
    calls, queue = http
    queue.append(FakeResponse(402, {"error": {"code": "usage_limit_reached"}}))
    with pytest.raises(QuotaExhausted):
        MarketauxProvider(api_token=SECRET).fetch_window_raw("NVDA", "2024-01-25", "2024-01-31")


# --- Key gating -----------------------------------------------------------------------

def _names(chain):
    return [p.name for p in chain]


def test_chains_unchanged_without_keys(monkeypatch):
    for var in KEY_VARS:
        monkeypatch.delenv(var, raising=False)
    assert _names(default_market_providers("equity")) == ["yahoo_finance"]
    assert _names(default_market_providers("crypto")) == ["yahoo_finance", "coincodex"]
    assert default_historical_news_providers() == []


def test_chains_with_all_keys(monkeypatch):
    for var in KEY_VARS:
        monkeypatch.setenv(var, SECRET)
    assert _names(default_market_providers("equity")) == ["yahoo_finance", "tiingo", "alpha_vantage"]
    assert _names(default_market_providers("crypto")) == ["yahoo_finance", "coincodex"]
    assert _names(default_historical_news_providers()) == ["finnhub", "alpha_vantage_news", "marketaux"]
