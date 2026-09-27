"""Canonical schemas shared by providers, features, models and dashboards."""
from __future__ import annotations

import pandas as pd

MARKET_COLUMNS = [
    "date", "asset_id", "open", "high", "low", "close", "adj_close", "volume",
    "market_cap", "currency", "source", "source_record_id", "ingested_at",
]

NEWS_COLUMNS = [
    "article_id", "published_at", "source", "publisher", "title", "description",
    "url", "entity", "ticker", "asset_type", "language", "ingested_at",
]


FACT_NEWS_RENAME = {"article_id": "news_id", "published_at": "timestamp", "publisher": "source_id"}


def to_fact_news(standardized: pd.DataFrame) -> pd.DataFrame:
    """Provider schema (article_id/published_at/publisher) → the fact_news
    schema (news_id/timestamp/source_id, DATA_MODEL.md §3.2) that sentiment,
    features and validation all key off."""
    return standardized.rename(columns=FACT_NEWS_RENAME)


def merge_news_frames(existing: pd.DataFrame | None, new: pd.DataFrame) -> pd.DataFrame:
    """Append new articles to the stored ones, one row per url. Existing rows
    win, so an article's news_id (and any sentiment already keyed to it) stays
    stable across runs."""
    if existing is None or existing.empty:
        combined = new.copy()
    else:
        combined = pd.concat([existing, new], ignore_index=True)
    combined = combined.drop_duplicates(subset=["url"], keep="first")
    return combined.sort_values("timestamp", kind="stable").reset_index(drop=True)


def standardize_market(df: pd.DataFrame, *, asset_id: str, source: str, currency: str = "USD") -> pd.DataFrame:
    out = df.copy()
    if "date" not in out.columns:
        raise ValueError("market data must contain date")
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.tz_localize(None)
    out["asset_id"] = out.get("asset_id", asset_id)
    out["currency"] = out.get("currency", currency)
    out["source"] = out.get("source", source)
    if "source_record_id" not in out.columns:
        out["source_record_id"] = [f"{asset_id}|{d}" for d in out["date"]]
    if "ingested_at" not in out.columns:
        out["ingested_at"] = pd.Timestamp.now("UTC").tz_localize(None)
    for col in ["open", "high", "low", "close", "adj_close", "volume", "market_cap"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
        else:
            out[col] = float("nan")
    return out[[c for c in MARKET_COLUMNS if c in out.columns]]


def repair_ohlc_bounds(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Widen high/low to contain open and close. Yahoo occasionally returns a
    row whose close sits just outside that day's high/low (seen on KRX tickers
    and on crypto's still-forming current-day candle), which would otherwise
    fail validate_market_prices and drop the whole asset. Returns the repaired
    frame and the number of rows changed."""
    if not {"open", "high", "low", "close"} <= set(df.columns):
        return df, 0
    out = df.copy()
    body_high = out[["open", "close"]].max(axis=1)
    body_low = out[["open", "close"]].min(axis=1)
    bad = (out["high"] < body_high) | (out["low"] > body_low)
    out["high"] = out["high"].where(out["high"] >= body_high, body_high)
    out["low"] = out["low"].where(out["low"] <= body_low, body_low)
    return out, int(bad.sum())


def standardize_news(df: pd.DataFrame, *, source: str = "unknown") -> pd.DataFrame:
    out = df.copy()
    rename = {"news_id": "article_id", "timestamp": "published_at", "source_id": "publisher"}
    out = out.rename(columns=rename)
    if "article_id" not in out.columns:
        out["article_id"] = out.get("url", pd.Series(dtype=str)).astype(str)
    if "published_at" not in out.columns:
        out["published_at"] = pd.NaT
    out["published_at"] = pd.to_datetime(out["published_at"], errors="coerce").dt.tz_localize(None)
    out["source"] = out.get("source", source)
    out["publisher"] = out.get("publisher", out["source"])
    for col, default in [("description", None), ("url", None), ("entity", None), ("ticker", None), ("asset_type", None), ("language", "en")]:
        if col not in out.columns:
            out[col] = default
    if "ingested_at" not in out.columns:
        out["ingested_at"] = pd.Timestamp.now("UTC").tz_localize(None)
    return out[[c for c in NEWS_COLUMNS if c in out.columns]]
