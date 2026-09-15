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
from src.features.sentiment_features import build_sentiment_features
from src.ingestion.universe import (
    build_market_universe,
    entity_to_market_map,
    load_companies,
    load_company_ai_categories,
)


def build_sector_members(universe: pd.DataFrame) -> dict[str, list[str]]:
    """{ai_category: [market_id, ...]} for equity market_ids only."""
    company_id_to_market_id = {
        row.company_id: row.market_id for row in universe.itertuples()
        if row.asset_type == "equity" and pd.notna(row.company_id)
    }
    categories = load_company_ai_categories()
    sector_members: dict[str, list[str]] = {}
    for _, row in categories.iterrows():
        market_id = company_id_to_market_id.get(row["company_id"])
        if market_id is None:
            continue
        sector_members.setdefault(row["ai_category"], []).append(market_id)
    return sector_members


def build_all_features(market_prices: dict[str, pd.DataFrame],
                        sentiment_df: pd.DataFrame | None = None,
                        news_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """market_prices: {market_id: OHLCV df}. Returns one combined long table:
    one row per (market_id, date), market + cross-sectional + (if sentiment
    data provided) sentiment features.
    """
    universe = build_market_universe()
    equity_market_ids = universe[universe["asset_type"] == "equity"]["market_id"].tolist()
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

        if sentiment_df is not None and news_df is not None and entity_id is not None:
            sentiment_features = build_sentiment_features(entity_id, sentiment_df, news_df, enriched["date"])
            enriched = enriched.merge(sentiment_features, on="date", how="left")

        combined_frames.append(enriched)

    result = pd.concat(combined_frames, ignore_index=True)
    return result.sort_values(["market_id", "date"]).reset_index(drop=True)
