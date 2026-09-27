"""Companies, themes (AI supply chain, energy, ...), thematic indices and AI events."""
from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, Depends

from api import data
from api.deps import get_settings
from api.settings import Settings
from src.analytics.indices import BENCHMARK_IDS, INDEX_MEMBERS, build_index_return, cumulative_return, rolling_correlation
from src.analytics.event_study import abnormal_return_window
from src.analytics.market_stats import add_returns

router = APIRouter(prefix="/api", tags=["reference"])


@router.get("/companies")
def companies() -> dict:
    comp = data.companies()
    themes = data.themes()
    funds = data.funds()
    ingested = set(data.market_ids())

    # themes.csv lists segments in display order (upstream to downstream).
    theme_order = list(dict.fromkeys(themes["theme"]))
    segments = {t: list(dict.fromkeys(themes.loc[themes["theme"] == t, "segment"])) for t in theme_order}

    by_entity = themes.groupby("entity_id")
    rows = comp.copy()
    rows["themes"] = rows["company_id"].map(
        lambda c: list(dict.fromkeys(by_entity.get_group(c)["theme"])) if c in by_entity.groups else [])
    rows["segments"] = rows["company_id"].map(
        lambda c: [f"{t} / {s}" for t, s in zip(by_entity.get_group(c)["theme"], by_entity.get_group(c)["segment"])]
        if c in by_entity.groups else [])
    rows["ingested"] = rows["ticker"].isin(ingested)

    # One row per (entity, theme, segment): companies and funds alike, each
    # linked to its market_id so every member is a priced, analysable asset.
    entities = pd.concat([
        pd.DataFrame({"entity_id": comp["company_id"], "name": comp["company_name"], "ticker": comp["ticker"],
                      "country": comp["country"], "region": comp["region"],
                      "kind": comp["ticker"].map(lambda t: "stock" if isinstance(t, str) else "private")}),
        pd.DataFrame({"entity_id": funds["fund_id"], "name": funds["fund_name"], "ticker": funds["ticker"],
                      "country": None, "region": None, "kind": funds["asset_class"]}),
    ], ignore_index=True)
    members = themes.merge(entities, on="entity_id", how="left")
    members["ingested"] = members["ticker"].isin(ingested)
    return data.clean({
        "companies": data.records(rows, date_cols=()),
        "themes": theme_order,
        "segments": segments,
        "regions": sorted(comp["region"].dropna().unique().tolist()),
        "theme_members": data.records(members, date_cols=()),
    })


def _returns_wide(settings: Settings) -> pd.DataFrame:
    series = {}
    for market_id in data.market_ids():
        df = data.market_prices(market_id, settings.excluded_sources)
        if df is not None and len(df) > 1:
            series[market_id] = add_returns(df[["date", "close"]]).set_index("date")["return_1d"]
    return pd.DataFrame(series).sort_index()


def _series(s: pd.Series) -> list[dict]:
    s = s.dropna()
    return [{"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 6)} for d, v in s.items()]


@router.get("/indices")
def indices(settings: Settings = Depends(get_settings)) -> dict:
    report = data.processed_json("indices_report.json") or {}
    wide = _returns_wide(settings)
    index_returns = {name: build_index_return(wide, members) for name, members in INDEX_MEMBERS.items()
                     if any(m in wide.columns for m in members)}
    for bench in BENCHMARK_IDS:
        if bench in wide.columns:
            index_returns[bench] = wide[bench]
    cumulative = {name: _series(cumulative_return(r)) for name, r in index_returns.items()}
    rolling_vs_spx = {}
    if "SPX" in wide.columns:
        for name in INDEX_MEMBERS:
            if name in index_returns:
                rolling_vs_spx[name] = _series(rolling_correlation(index_returns[name], wide["SPX"], window=30))
    return data.clean({**report, "cumulative_return": cumulative, "rolling_corr_vs_spx": rolling_vs_spx})


def _event_windows(outcomes: list[dict], benchmark: str | None, window: int | None,
                   settings: Settings) -> dict[str, list[dict]]:
    """Daily abnormal returns around each event, recomputed from cached prices
    with the same function the event study used (src.analytics.event_study)."""
    if not benchmark or not window:
        return {}
    bench = data.market_prices(benchmark, settings.excluded_sources)
    if bench is None:
        return {}
    bench = add_returns(bench[["date", "close"]])
    windows = {}
    for o in outcomes:
        if o.get("status") != "OK":
            continue
        asset = data.market_prices(o["market_id"], settings.excluded_sources)
        if asset is None:
            continue
        asset = add_returns(asset[["date", "close"]])
        ar = abnormal_return_window(asset["return_1d"], asset["date"], bench["return_1d"], bench["date"],
                                    o["event_date"], window)
        if ar is not None:
            windows[o["event_id"]] = [{"day": int(d), "value": float(v)} for d, v in ar.items()]
    return windows


@router.get("/events")
def events(settings: Settings = Depends(get_settings)) -> dict:
    ev = data.events()
    if not ev.empty:
        ev = ev.assign(source="curated")
    detected = data.detected_events()
    if not detected.empty:
        detected = detected.assign(source="news").drop(columns=["first_headline"], errors="ignore")
        ev = pd.concat([ev, detected], ignore_index=True)
    report = data.processed_json("event_study_report.json") or {}
    caar = data.processed_csv("event_study_caar.csv")
    caar_rows = []
    if caar is not None:
        caar = caar.rename(columns={caar.columns[0]: "day"})
        caar_rows = data.records(caar, date_cols=())
    return data.clean({
        "events": data.records(ev, date_cols=()) if not ev.empty else [],
        "benchmark": report.get("benchmark"),
        "window": report.get("window"),
        "outcomes": report.get("events", []),
        "abnormal_returns": _event_windows(report.get("events", []), report.get("benchmark"),
                                           report.get("window"), settings),
        "caar": caar_rows,
    })
