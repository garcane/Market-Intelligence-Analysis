"""Orchestrates the full Stage 6 feature pipeline: for every ingested asset,
build market + sentiment + cross-sectional features and combine into one
row per (market_id, date), each with an explicit `date` timestamp.

AI event features (model release indicator, benchmark improvement, company
event indicator) are intentionally NOT included — no event data source has
been ingested (fact_model_release / fact_company_event don't exist yet; that's
Stage 11 event-study prerequisite work). Adding zero-filled placeholder columns
here would look like a feature without being one; the gap is documented in
FEATURES.md and CHECKPOINT.md instead.
"""
from __future__ import annotations

import pandas as pd

from src.features.cross_sectional_features import (
    add_cross_sectional_features,
    build_returns_wide,
    compute_ai_index_return,
    compute_market_return,
    compute_sector_returns,
)
from src.features.market_features import build_market_features
from src.features.sentiment_features import SENTIMENT_FEATURE_COLUMNS, build_sentiment_features
from src.ingestion.universe import (
    build_market_universe,
    entity_to_market_map,
    load_companies,
    load_themes,
)

SECTOR_FEATURE_COLUMNS = ["sector_return", "relative_sector_performance"]


AI_THEMES = ("AI Supply Chain", "AI Models", "AI Applications")


def _company_market_ids(universe: pd.DataFrame) -> dict[str, str]:
    return {row.company_id: row.market_id for row in universe.itertuples()
            if row.asset_type == "equity" and pd.notna(row.company_id)}


def build_sector_members(universe: pd.DataFrame) -> dict[str, list[str]]:
    """{"theme / segment": [market_id, ...]} for equity market_ids only
    (data/reference/themes.csv), e.g. "AI Supply Chain / Semiconductors"."""
    company_id_to_market_id = _company_market_ids(universe)
    sector_members: dict[str, list[str]] = {}
    for _, row in load_themes().iterrows():
        market_id = company_id_to_market_id.get(row["entity_id"])
        if market_id is None:
            continue
        sector_members.setdefault(f"{row['theme']} / {row['segment']}", []).append(market_id)
    return sector_members


def ai_equity_market_ids(universe: pd.DataFrame) -> list[str]:
    """Stocks tagged with an AI theme. Energy-only names (oil majors, solar)
    are tracked stocks too but are kept out of the AI index feature."""
    company_id_to_market_id = _company_market_ids(universe)
    themes = load_themes()
    ai_entities = themes.loc[themes["theme"].isin(AI_THEMES), "entity_id"]
    return sorted({company_id_to_market_id[e] for e in ai_entities if e in company_id_to_market_id})


def build_all_features(market_prices: dict[str, pd.DataFrame],
                        sentiment_df: pd.DataFrame | None = None,
                        news_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """market_prices: {market_id: OHLCV df}. Returns one combined long table:
    one row per (market_id, date), market + cross-sectional + (if sentiment
    data provided) sentiment features.
    """
    universe = build_market_universe()
    equity_market_ids = ai_equity_market_ids(universe)
    market_id_to_entity = {v: k for k, v in entity_to_market_map().items()}
    sector_members = build_sector_members(universe)

    market_features_by_id: dict[str, pd.DataFrame] = {}
    returns_for_xsec: dict[str, pd.DataFrame] = {}
    for market_id, df in market_prices.items():
        features = build_market_features(df)
        market_features_by_id[market_id] = features
        returns_for_xsec[market_id] = features[["date", "return_1d"]]

    returns_wide = build_returns_wide(returns_for_xsec)
    market_return = compute_market_return(returns_wide)
    ai_index_return = compute_ai_index_return(returns_wide, equity_market_ids)
    sector_returns = compute_sector_returns(returns_wide, sector_members)

    combined_frames = []
    for market_id, features in market_features_by_id.items():
        entity_id = market_id_to_entity.get(market_id)
        sector_label = next((s for s, members in sector_members.items() if market_id in members), None)
        sector_series = sector_returns[sector_label] if sector_label in sector_returns.columns else None

        enriched = add_cross_sectional_features(features, market_return, ai_index_return, sector_series)
        enriched.insert(0, "market_id", market_id)

        if sentiment_df is not None and news_df is not None:
            # Called even when entity_id is None (asset has no matched entity
            # in the news universe, e.g. a crypto asset or one added to the
            # universe without sentiment coverage) — build_sentiment_features
            # already handles "no matching news" by returning NaN-filled
            # columns (see its docstring), so this keeps the sentiment columns
            # structurally present for every asset rather than silently
            # omitting them, which would break any downstream code (like
            # src/models/dataset.py's fixed feature whitelist) that assumes
            # every asset's feature row has the same columns.
            sentiment_features = build_sentiment_features(entity_id, sentiment_df, news_df, enriched["date"])
            enriched = enriched.merge(sentiment_features, on="date", how="left")

        combined_frames.append(enriched)

    result = pd.concat(combined_frames, ignore_index=True)

    # Guarantee a stable schema: sentiment and sector columns exist (as float
    # NaN) even when no sentiment data was supplied or no asset in the batch
    # has a sector match. Missing-value representation failed in six places
    # this project (see FAILURE_LOG.md); consumers had been patched one by
    # one, so the producer now owns the contract instead.
    for col in SENTIMENT_FEATURE_COLUMNS + SECTOR_FEATURE_COLUMNS:
        if col not in result.columns:
            result[col] = float("nan")

    return result.sort_values(["market_id", "date"]).reset_index(drop=True)
