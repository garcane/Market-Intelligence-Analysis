"""Market prices, per-asset statistics and the return correlation matrix."""
from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from api import data
from api.deps import get_settings
from api.settings import Settings
from src.analytics.market_stats import add_returns, compute_market_stats, summary_stats
from src.features.target import MODELING_MARKET_IDS

router = APIRouter(prefix="/api/markets", tags=["markets"])

SPARK_POINTS = 60
SPARK_DAYS = 180


def describe(market_id: str) -> dict:
    """Name, kind (stock | etf | index | crypto), currency and categories."""
    info = data.universe().get(market_id, {})
    return {
        "name": info.get("name") or market_id,
        "kind": info.get("kind", "stock"),
        "currency": info.get("currency"),
        "categories": info.get("categories", []),
        "segments": info.get("segments", []),
        "rank": info.get("rank"),
    }


def _load(market_id: str, settings: Settings) -> pd.DataFrame:
    if market_id not in data.market_ids():
        raise HTTPException(404, f"unknown market_id {market_id!r}")
    df = data.market_prices(market_id, settings.excluded_sources)
    if df is None or df.empty:
        raise HTTPException(404, f"no price data for {market_id!r}")
    return df


def _sparkline(df: pd.DataFrame) -> list[float]:
    recent = df[df["date"] >= df["date"].max() - pd.Timedelta(days=SPARK_DAYS)]["close"]
    step = max(1, len(recent) // SPARK_POINTS)
    return [round(float(v), 4) for v in recent.iloc[::step]]


@router.get("")
def list_markets(settings: Settings = Depends(get_settings)) -> list[dict]:
    rows = []
    for market_id in data.market_ids():
        df = data.market_prices(market_id, settings.excluded_sources)
        if df is None or df.empty:
            continue
        stats = compute_market_stats(df)
        rows.append({
            "market_id": market_id,
            **describe(market_id),
            "modelled": market_id in MODELING_MARKET_IDS,
            "last_close": float(stats["close"].iloc[-1]),
            "change_1d": float(stats["return_1d"].iloc[-1]),
            **summary_stats(stats),
            "spark": _sparkline(stats),
        })
    return data.clean(rows)


@router.get("/correlation")
def correlation(ids: str | None = Query(None, description="comma-separated market_ids; default all"),
                settings: Settings = Depends(get_settings)) -> dict:
    wanted = [i for i in (ids.split(",") if ids else data.market_ids()) if i in data.market_ids()]
    series = {}
    for market_id in wanted:
        df = data.market_prices(market_id, settings.excluded_sources)
        if df is not None and len(df) > 1:
            series[market_id] = add_returns(df[["date", "close"]]).set_index("date")["return_1d"]
    corr = pd.DataFrame(series).corr()
    return data.clean({"ids": list(corr.columns), "matrix": corr.round(4).values.tolist()})


@router.get("/{market_id}/prices")
def prices(market_id: str, start: date | None = None, end: date | None = None,
           settings: Settings = Depends(get_settings)) -> dict:
    df = _load(market_id, settings)
    if start:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end:
        df = df[df["date"] <= pd.Timestamp(end)]
    if df.empty:
        raise HTTPException(404, "no prices in the requested range")
    stats = compute_market_stats(df)
    cols = ["date", "open", "high", "low", "close", "volume", "return_1d",
            "cumulative_return", "drawdown", "rolling_vol_30d"]
    full = data.market_prices(market_id, settings.excluded_sources)
    return data.clean({
        "market_id": market_id,
        **describe(market_id),
        "available_range": [str(full["date"].min().date()), str(full["date"].max().date())],
        "sources": sorted(df["source"].dropna().unique().tolist()) if "source" in df else [],
        "summary": summary_stats(stats),
        "rows": data.records(stats[cols]),
    })
