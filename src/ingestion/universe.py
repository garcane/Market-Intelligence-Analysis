"""Builds the dim_market universe (equities + crypto) from the Stage 1 reference
tables. This is the single source of truth for "which instruments do we track" —
ingestion, features, and the dashboard all derive their asset list from here
rather than hard-coding ticker lists.
"""
from __future__ import annotations

import pandas as pd

from src.config import REFERENCE_DIR


def load_companies() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "companies.csv")


def load_company_ai_categories() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "company_ai_categories.csv")


def load_crypto_assets() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "crypto_assets.csv")


def build_market_universe() -> pd.DataFrame:
    """Returns a dim_market-shaped DataFrame:
    market_id, asset_type, company_id, crypto_asset_id, symbol, currency, exchange
    """
    companies = load_companies()
    public = companies[companies["is_public"] & companies["ticker"].notna()].copy()
    equity_rows = pd.DataFrame({
        "market_id": public["ticker"],
        "asset_type": "equity",
        "company_id": public["company_id"],
        "crypto_asset_id": pd.NA,
        "symbol": public["ticker"],
        "currency": "USD",
        "exchange": public["exchange"],
    })

    crypto = load_crypto_assets()
    crypto_rows = pd.DataFrame({
        "market_id": crypto["symbol"],
        "asset_type": "crypto",
        "company_id": pd.NA,
        "crypto_asset_id": crypto["asset_id"],
        "symbol": crypto["symbol"] + "-USD",  # yfinance crypto convention
        "currency": "USD",
        "exchange": pd.NA,
    })

    universe = pd.concat([equity_rows, crypto_rows], ignore_index=True)
    duplicates = universe[universe["market_id"].duplicated(keep=False)]
    if not duplicates.empty:
        raise ValueError(f"Duplicate market_id in universe:\n{duplicates}")
    return universe


def entity_to_market_map() -> dict[str, str]:
    """Maps every matched_company_id / matched_asset_id (as used in fact_news)
    to its market_id in dim_market, for entities that are actually tracked with
    price data. Companies with no ticker (private labs) and crypto assets not
    in the tracked universe are simply absent from the returned mapping.
    """
    universe = build_market_universe()
    company_map = {
        row.company_id: row.market_id
        for row in universe.itertuples()
        if row.asset_type == "equity" and pd.notna(row.company_id)
    }
    crypto_map = {
        row.crypto_asset_id: row.market_id
        for row in universe.itertuples()
        if row.asset_type == "crypto" and pd.notna(row.crypto_asset_id)
    }
    return {**company_map, **crypto_map}
