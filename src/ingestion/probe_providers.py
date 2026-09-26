"""Probe what each keyed provider's plan actually allows, before relying on it.

Makes a handful of small requests (about 5 of Alpha Vantage's ~25/day) and
prints one row per capability. Tokens are never
printed: provider errors are redacted in providers.get_json.

Run as: python -m src.ingestion.probe_providers
"""
from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable
from datetime import date, timedelta

import pandas as pd

from src.config import PROCESSED_DIR, RAW_DIR
from src.ingestion.base import AccessDenied, ProviderError, QuotaExhausted
from src.ingestion.providers import (
    AlphaVantageMarketProvider,
    AlphaVantageNewsProvider,
    FinnhubNewsProvider,
    TiingoProvider,
    YahooFinanceNewsProvider,
    get_json,
)
from src.ingestion.providers_health import write_health_report

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

ALPHA_VANTAGE_SPACING_SECONDS = 13  # free tier also limits bursts


def _run(capability: str, env_var: str | None, fn: Callable[[], str]) -> dict:
    if env_var and not os.getenv(env_var):
        return {"capability": capability, "status": "NO KEY", "detail": f"{env_var} not set"}
    try:
        return {"capability": capability, "status": "OK", "detail": fn()}
    except QuotaExhausted as exc:
        return {"capability": capability, "status": "QUOTA", "detail": str(exc)[:160]}
    except AccessDenied as exc:
        return {"capability": capability, "status": "BLOCKED", "detail": str(exc)[:160]}
    except ProviderError as exc:
        return {"capability": capability, "status": "ERROR", "detail": str(exc)[:160]}


def _window(months_back: int, days: int = 7) -> tuple[str, str]:
    end = date.today() - timedelta(days=30 * months_back)
    return (end - timedelta(days=days - 1)).isoformat(), end.isoformat()


def _count(parse_frame: pd.DataFrame) -> str:
    if parse_frame.empty:
        return "0 articles"
    ts = pd.to_datetime(parse_frame["published_at"])
    return f"{len(parse_frame)} articles, {ts.min().date()}..{ts.max().date()}"


def probe_tiingo() -> str:
    """NVDA across its 2024 10:1 split: the split-adjusted close must match Yahoo."""
    today = date.today().isoformat()
    df = TiingoProvider().fetch_prices("NVDA", "2023-06-01", today)
    detail = f"{len(df)} rows from {df['date'].min().date()}"
    yahoo_path = RAW_DIR / "market_prices" / "NVDA.parquet"
    if yahoo_path.exists():
        yahoo = pd.read_parquet(yahoo_path, columns=["date", "close"])
        joined = df[["date", "close"]].merge(yahoo, on="date", suffixes=("_tiingo", "_yahoo"))
        worst = ((joined["close_tiingo"] / joined["close_yahoo"]) - 1).abs().max()
        detail += f"; max |close diff| vs Yahoo over {len(joined)} days: {worst:.4%}"
    return detail


def probe_alpha_vantage_daily(outputsize: str) -> Callable[[], str]:
    def run() -> str:
        start = (date.today() - timedelta(days=60)).isoformat()
        df = AlphaVantageMarketProvider(outputsize=outputsize).fetch_prices("NVDA", start, date.today().isoformat())
        return f"{len(df)} rows from {df['date'].min().date()}"
    return run


def probe_finnhub_candles() -> str:
    key = os.getenv("FINNHUB_API_KEY")
    end = int(time.time())
    payload = get_json("https://finnhub.io/api/v1/stock/candle", provider="finnhub", secrets=(key,),
                       params={"symbol": "NVDA", "resolution": "D", "from": end - 30 * 86400, "to": end},
                       headers={"X-Finnhub-Token": key})
    if isinstance(payload, dict) and payload.get("error"):
        raise AccessDenied(f"finnhub: {payload['error']}")
    return f"status={payload.get('s')}, {len(payload.get('c') or [])} closes"


def probe_news(provider, symbol: str, months_back: int, days: int) -> Callable[[], str]:
    def run() -> str:
        start, end = _window(months_back, days)
        return f"{start}..{end}: " + _count(provider.fetch_window(symbol, start, end))
    return run


def main() -> None:
    rows = []
    rows.append(_run("tiingo daily history (NVDA, split check)", "TIINGO_API_TOKEN", probe_tiingo))

    rows.append(_run("alpha_vantage TIME_SERIES_DAILY full", "ALPHA_VANTAGE_API_KEY",
                     probe_alpha_vantage_daily("full")))
    time.sleep(ALPHA_VANTAGE_SPACING_SECONDS)
    rows.append(_run("alpha_vantage TIME_SERIES_DAILY compact", "ALPHA_VANTAGE_API_KEY",
                     probe_alpha_vantage_daily("compact")))

    rows.append(_run("finnhub stock candles", "FINNHUB_API_KEY", probe_finnhub_candles))
    finnhub = FinnhubNewsProvider()
    for months in (1, 11, 13, 24):
        rows.append(_run(f"finnhub company news, {months} months back", "FINNHUB_API_KEY",
                         probe_news(finnhub, "NVDA", months, days=7)))
        time.sleep(finnhub.min_interval_seconds)

    yahoo_news = YahooFinanceNewsProvider()
    for symbol in ("NVDA", "BTC-USD"):
        rows.append(_run(f"yahoo_finance news {symbol} (latest only, keyless)", None,
                         lambda s=symbol: _count(yahoo_news.fetch_news(s))))

    av_news = AlphaVantageNewsProvider()
    for symbol, months in (("NVDA", 13), ("NVDA", 24), ("CRYPTO:BTC", 1)):
        time.sleep(ALPHA_VANTAGE_SPACING_SECONDS)
        rows.append(_run(f"alpha_vantage news {symbol}, {months} months back", "ALPHA_VANTAGE_API_KEY",
                         probe_news(av_news, symbol, months, days=30)))

    width = max(len(r["capability"]) for r in rows)
    for r in rows:
        print(f"{r['capability']:<{width}}  {r['status']:<8}  {r['detail']}")
    write_health_report({"run_date": date.today().isoformat(), "results": rows},
                        PROCESSED_DIR / "provider_probe.json")


if __name__ == "__main__":
    main()
