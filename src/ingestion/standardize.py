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
