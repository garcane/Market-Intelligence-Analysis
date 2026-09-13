"""Market price ingestion via yfinance, with retries/backoff/timeout handling.
API-based (yfinance wraps Yahoo Finance's API), not HTML scraping, per the
target spec's preference for APIs over brittle scraping.
"""
from __future__ import annotations

import logging
import time

import pandas as pd
import yfinance as yf

import src.config  # noqa: F401 - side effect: ensures CURL_CA_BUNDLE is set before any yf.download call

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 30


class FetchError(Exception):
    pass


def _normalize_columns(raw: pd.DataFrame) -> pd.DataFrame:
    """yfinance returns a MultiIndex-or-flat frame depending on version/args;
    normalize to the flat schema the rest of the pipeline expects."""
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low", "Close": "close",
        "Adj Close": "adj_close", "Volume": "volume",
    })
    df = df.reset_index().rename(columns={"Date": "date"})
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
    keep = [c for c in ["date", "open", "high", "low", "close", "adj_close", "volume"] if c in df.columns]
    return df[keep]


def fetch_market_prices(symbol: str, start: str, end: str,
                         max_retries: int = MAX_RETRIES) -> pd.DataFrame:
    """Fetch OHLCV for one symbol between start/end (YYYY-MM-DD), with retries.
    Raises FetchError if all retries are exhausted or the response is empty.
    """
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            raw = yf.download(
                symbol, start=start, end=end, progress=False,
                timeout=REQUEST_TIMEOUT_SECONDS, auto_adjust=False,
            )
            if raw is None or raw.empty:
                raise FetchError(f"empty response for symbol={symbol}")
            df = _normalize_columns(raw)
            if "market_cap" not in df.columns:
                # float NaN (not pd.NA) so the column stays a plain numeric dtype
                # that round-trips identically through parquet.
                df["market_cap"] = float("nan")
            return df
        except Exception as exc:  # noqa: BLE001 - deliberately broad: network/library errors of many types
            last_error = exc
            logger.warning("fetch attempt %d/%d failed for %s: %s", attempt, max_retries, symbol, exc)
            if attempt < max_retries:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise FetchError(f"all {max_retries} attempts failed for symbol={symbol}: {last_error}")
