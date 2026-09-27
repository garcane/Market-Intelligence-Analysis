"""Read-only access to the pipeline's saved outputs. Nothing here fetches live
data or trains a model; the API only serves what the pipeline has written.

Each reader is cached on the file's modification time, so a pipeline run shows
up on the next request without restarting the server. Cached frames are shared
between requests: callers must copy before mutating.
"""
from __future__ import annotations

import json
import math
import threading
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from src.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR, REFERENCE_DIR

MARKET_DIR = RAW_DIR / "market_prices"
NEWS_PATH = RAW_DIR / "news" / "news.parquet"
SENTIMENT_PATH = RAW_DIR / "sentiment" / "fact_sentiment.parquet"
FIGURES_DIR = OUTPUTS_DIR / "figures"

_cache: dict[tuple[str, str], tuple[int, Any]] = {}
_lock = threading.Lock()


def cached_read(path: Path, reader: Callable[[Path], Any]) -> Any:
    """reader(path), memoised until the file changes. None if the file is missing."""
    try:
        mtime = path.stat().st_mtime_ns
    except FileNotFoundError:
        return None
    key = (str(path), reader.__qualname__)
    with _lock:
        hit = _cache.get(key)
    if hit and hit[0] == mtime:
        return hit[1]
    value = reader(path)
    with _lock:
        _cache[key] = (mtime, value)
    return value


def clear_cache() -> None:
    with _lock:
        _cache.clear()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> pd.DataFrame | None:
    return cached_read(path, pd.read_csv)


def read_parquet(path: Path) -> pd.DataFrame | None:
    return cached_read(path, pd.read_parquet)


def read_json(path: Path) -> Any:
    return cached_read(path, _read_json)


# --- reference data ---------------------------------------------------------

def companies() -> pd.DataFrame:
    return read_csv(REFERENCE_DIR / "companies.csv")


def themes() -> pd.DataFrame:
    return read_csv(REFERENCE_DIR / "themes.csv")


def funds() -> pd.DataFrame:
    return read_csv(REFERENCE_DIR / "funds.csv")


def crypto_assets() -> pd.DataFrame:
    return read_csv(REFERENCE_DIR / "crypto_assets.csv")


def events() -> pd.DataFrame:
    df = read_csv(REFERENCE_DIR / "events.csv")
    return df if df is not None else pd.DataFrame()


def detected_events() -> pd.DataFrame:
    df = read_csv(PROCESSED_DIR / "detected_events.csv")
    return df if df is not None else pd.DataFrame()


# --- the tracked universe -------------------------------------------------------

UNIVERSE_FILES = ("companies.csv", "funds.csv", "themes.csv", "crypto_assets.csv")
KIND = {"equity": "stock", "etf": "etf", "index": "index", "crypto": "crypto"}


def _build_universe() -> dict[str, dict]:
    from src.ingestion.universe import build_market_universe, market_categories

    table = build_market_universe()
    categories = market_categories(table)
    crypto = crypto_assets()
    ranks = dict(zip(crypto["symbol"], crypto["rank"])) if crypto is not None and "rank" in crypto else {}
    return {
        row.market_id: {
            "name": row.name,
            "kind": KIND.get(row.asset_type, row.asset_type),
            "currency": row.currency if isinstance(row.currency, str) else None,
            "exchange": row.exchange if isinstance(row.exchange, str) else None,
            "company_id": row.company_id if isinstance(row.company_id, str) else None,
            "rank": ranks.get(row.market_id),
            **categories[row.market_id],
        }
        for row in table.itertuples()
    }


def universe() -> dict[str, dict]:
    """market_id -> name, kind (stock | etf | index | crypto), currency,
    categories and theme segments, rebuilt whenever a reference table changes."""
    stamp = tuple((REFERENCE_DIR / f).stat().st_mtime_ns for f in UNIVERSE_FILES)
    key = ("universe", str(REFERENCE_DIR))
    with _lock:
        hit = _cache.get(key)
    if hit and hit[0] == stamp:
        return hit[1]
    value = _build_universe()
    with _lock:
        _cache[key] = (stamp, value)
    return value


# --- market, news and sentiment ------------------------------------------------

def market_ids() -> list[str]:
    """Ingested instruments that are in the current universe. A price file
    left behind by an instrument that has since left the universe (e.g. a coin
    that dropped out of the crypto top 10) is not served."""
    if not MARKET_DIR.exists():
        return []
    tracked = universe()
    return sorted(p.stem for p in MARKET_DIR.glob("*.parquet") if p.stem in tracked)


def market_prices(market_id: str, excluded_sources: frozenset[str] = frozenset()) -> pd.DataFrame | None:
    df = read_parquet(MARKET_DIR / f"{market_id}.parquet")
    if df is None:
        return None
    if excluded_sources and "source" in df.columns:
        df = df[~df["source"].isin(excluded_sources)]
    return df.sort_values("date").reset_index(drop=True)


def news() -> pd.DataFrame | None:
    return read_parquet(NEWS_PATH)


def sentiment() -> pd.DataFrame | None:
    return read_parquet(SENTIMENT_PATH)


def processed_json(name: str) -> Any:
    return read_json(PROCESSED_DIR / name)


def processed_csv(name: str) -> pd.DataFrame | None:
    return read_csv(PROCESSED_DIR / name)


# --- JSON conversion ----------------------------------------------------------

def clean(value: Any) -> Any:
    """Make a value JSON-safe: NaN/inf become null, numpy scalars become Python."""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def records(df: pd.DataFrame, date_cols: tuple[str, ...] = ("date",)) -> list[dict]:
    """DataFrame -> list of dicts, dates as YYYY-MM-DD, NaN as null."""
    df = df.copy()
    for col in df.columns:
        if col in date_cols or pd.api.types.is_datetime64_any_dtype(df[col]):
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                fmt = "%Y-%m-%d" if col in date_cols else "%Y-%m-%dT%H:%M:%S"
                df[col] = df[col].dt.strftime(fmt)
            else:
                df[col] = df[col].astype(str)
    return json.loads(df.to_json(orient="records"))
