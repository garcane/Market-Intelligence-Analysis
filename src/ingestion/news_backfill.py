"""Resumable historical news backfill.

Free news quotas are small (Marketaux 100 requests/day, Alpha Vantage ~25),
so the backfill runs a little each day, newest window first, and picks up
where it stopped:

- Every successful (provider, market, window) response is cached raw under
  data/raw/news_backfill/. A cached window is never requested again, which
  includes windows that came back empty. Failed requests are not cached.
- A per-provider state file tracks today's request count. QuotaExhausted
  stops that provider for the day; the others carry on.
- Merging parses the cache, so a parser fix never costs quota.
"""
from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import RAW_DIR
from src.ingestion.base import AccessDenied, HistoricalNewsProvider, ProviderError, QuotaExhausted
from src.ingestion.providers import AlphaVantageNewsProvider, FinnhubNewsProvider, MarketauxProvider
from src.ingestion.standardize import to_fact_news

logger = logging.getLogger(__name__)

CACHE_ROOT = RAW_DIR / "news_backfill"
DEFAULT_EARLIEST = date(2023, 6, 1)
PARSERS: dict[str, Callable[[Any], pd.DataFrame]] = {
    cls.name: cls.parse_window
    for cls in (FinnhubNewsProvider, AlphaVantageNewsProvider, MarketauxProvider)
}


def plan_windows(latest: date, earliest: date, window_days: int) -> list[tuple[date, date]]:
    """Contiguous (start, end) windows covering [earliest, latest], newest first."""
    windows = []
    end = latest
    while end >= earliest:
        start = max(end - timedelta(days=window_days - 1), earliest)
        windows.append((start, end))
        end = start - timedelta(days=1)
    return windows


def cache_path(root: Path, provider: str, market_id: str, start: date) -> Path:
    return root / provider / market_id / f"{start.isoformat()}.json"


def _load_state(path: Path, today: date) -> dict:
    state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for entry in state.values():  # counters reset each day
        if entry.get("date") != today.isoformat():
            entry.update(date=today.isoformat(), requests=0, stopped=None)
    return state


def _save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def run_backfill(providers: list[HistoricalNewsProvider], markets: list[tuple[str, str]], *,
                 latest: date | None = None, earliest: date = DEFAULT_EARLIEST,
                 max_requests: int | None = None, cache_root: Path = CACHE_ROOT,
                 sleep: Callable[[float], None] = time.sleep) -> dict:
    """Fetch uncached windows, newest first, within each provider's budget.
    `markets` is a list of (market_id, asset_type). Returns a summary dict."""
    today = date.today()
    latest = latest or today
    state_path = cache_root / "_state.json"
    state = _load_state(state_path, today)
    summary: dict[str, dict] = {}
    total_requests = 0

    for provider in providers:
        entry = state.setdefault(provider.name, {"date": today.isoformat(), "requests": 0, "stopped": None})
        stats = summary.setdefault(provider.name, {"fetched": 0, "cached_skipped": 0, "articles": 0,
                                                   "failed": 0, "stopped": entry["stopped"]})
        if entry["stopped"]:
            logger.info("%s: already stopped today (%s)", provider.name, entry["stopped"])
            continue
        first_call = True
        provider_earliest = earliest
        if provider.history_limit_days is not None:
            provider_earliest = max(earliest, today - timedelta(days=provider.history_limit_days))
        for start, end in plan_windows(latest, provider_earliest, provider.window_days):
            if entry["stopped"]:
                break
            for market_id, asset_type in markets:
                symbol = provider.provider_symbol(market_id, asset_type)
                if symbol is None:
                    continue
                path = cache_path(cache_root, provider.name, market_id, start)
                if path.exists():
                    stats["cached_skipped"] += 1
                    continue
                if max_requests is not None and total_requests >= max_requests:
                    stats["stopped"] = "max_requests reached"
                    _save_state(state_path, state)
                    return summary
                budget = provider.daily_request_budget
                if budget is not None and entry["requests"] >= budget:
                    entry["stopped"] = stats["stopped"] = f"daily budget of {budget} used"
                    break
                if not first_call:
                    sleep(getattr(provider, "min_interval_seconds", 0.0))
                first_call = False
                entry["requests"] += 1
                total_requests += 1
                try:
                    raw = provider.fetch_window_raw(symbol, start.isoformat(), end.isoformat())
                except QuotaExhausted as exc:
                    entry["stopped"] = stats["stopped"] = f"quota exhausted: {exc}"
                    break
                except AccessDenied as exc:
                    entry["stopped"] = stats["stopped"] = f"access denied: {exc}"
                    break
                except ProviderError as exc:
                    stats["failed"] += 1
                    logger.warning("%s %s %s: %s", provider.name, market_id, start, exc)
                    continue
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({
                    "provider": provider.name, "market_id": market_id, "symbol": symbol,
                    "start": start.isoformat(), "end": end.isoformat(),
                    "fetched_at": datetime.now(timezone.utc).isoformat(), "raw": raw,
                }), encoding="utf-8")
                stats["fetched"] += 1
                stats["articles"] += len(provider.parse_window(raw))
        _save_state(state_path, state)
        logger.info("%s: %s", provider.name, stats)
    return summary


def merge_backfill(cache_root: Path, entity_by_market: dict[str, tuple[str, str]]) -> pd.DataFrame:
    """Parse every cached window into fact_news rows. `entity_by_market` maps
    market_id → (entity_id, asset_type); the article is attributed to the
    market it was queried for, which is more precise than matching names in
    headlines."""
    frames = []
    for path in sorted(cache_root.glob("*/*/*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        parser = PARSERS.get(record["provider"])
        entity = entity_by_market.get(record["market_id"])
        if parser is None or entity is None:
            continue
        df = parser(record["raw"])
        if df.empty:
            continue
        entity_id, asset_type = entity
        df = to_fact_news(df)
        df["entity"] = record["market_id"]
        df["matched_company_id"] = entity_id if asset_type == "equity" else None
        df["matched_asset_id"] = entity_id if asset_type == "crypto" else None
        df["category"] = "general"
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates(subset=["url"], keep="first")


def coverage_report(news_df: pd.DataFrame, trading_dates: dict[str, pd.Series],
                    entity_by_market: dict[str, tuple[str, str]], train_end: str, val_end: str) -> dict:
    """Share of each market's trading days with at least one matched article,
    by split period. Counts exact dates only, the way the sentiment features
    join news onto prices, so it is the conservative measure."""
    train_end_ts, val_end_ts = pd.Timestamp(train_end), pd.Timestamp(val_end)
    news_dates = pd.to_datetime(news_df["timestamp"]).dt.normalize() if not news_df.empty else pd.Series(dtype="datetime64[ns]")
    report: dict[str, Any] = {"by_market": {}, "totals": {}}
    totals = {p: [0, 0] for p in ("train", "validation", "test")}

    for market_id, dates in trading_dates.items():
        entity_id, _ = entity_by_market.get(market_id, (None, None))
        if news_df.empty or entity_id is None:
            article_days = set()
        else:
            mask = (news_df.get("matched_company_id") == entity_id) | (news_df.get("matched_asset_id") == entity_id)
            article_days = set(news_dates[mask.fillna(False)])
        days = pd.to_datetime(pd.Series(dates)).dt.normalize()
        periods = {
            "train": days[days <= train_end_ts],
            "validation": days[(days > train_end_ts) & (days <= val_end_ts)],
            "test": days[days > val_end_ts],
        }
        market_report = {}
        for period, period_days in periods.items():
            covered = int(period_days.isin(article_days).sum())
            market_report[period] = {"days": len(period_days), "covered": covered,
                                     "pct": round(covered / len(period_days), 4) if len(period_days) else None}
            totals[period][0] += len(period_days)
            totals[period][1] += covered
        report["by_market"][market_id] = market_report

    for period, (n_days, n_covered) in totals.items():
        report["totals"][period] = {"days": n_days, "covered": n_covered,
                                    "pct": round(n_covered / n_days, 4) if n_days else None}
    return report
