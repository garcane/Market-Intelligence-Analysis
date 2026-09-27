"""Builds the dim_market universe (stocks, ETFs, indices and crypto) from the
reference tables. This is the single source of truth for "which instruments do
we track" — ingestion, features, analytics and the web app all derive their
asset lists and categories from here rather than hard-coding ticker lists.

Reference tables (data/reference/):
- companies.csv          one row per company, public or private
- funds.csv              ETFs and indices (benchmarks and thematic funds)
- themes.csv             bridge: entity (company_id or fund_id) -> theme / segment
- crypto_assets.csv      the current top-N crypto universe, written by
                         src.ingestion.crypto_universe from CoinCodex rankings
"""
from __future__ import annotations

import pandas as pd

from src.config import REFERENCE_DIR

# Top-level categories shown in the web app, in display order. Themes come
# from themes.csv; the other three come from each instrument's asset class.
STOCKS, BENCHMARKS, CRYPTO = "Stocks", "Benchmarks", "Crypto"
CATEGORY_ORDER = [STOCKS, "AI Supply Chain", "Energy", "AI Models", "AI Applications", BENCHMARKS, CRYPTO]


def load_companies() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "companies.csv")


def load_funds() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "funds.csv")


def load_themes() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "themes.csv")


def load_crypto_assets() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "crypto_assets.csv")


def _is_true(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower() == "true"


def build_market_universe() -> pd.DataFrame:
    """Returns a dim_market-shaped DataFrame, one row per tracked instrument:
    market_id, asset_type (equity | etf | index | crypto), name, company_id,
    fund_id, crypto_asset_id, symbol (provider symbol), currency, exchange.
    """
    companies = load_companies()
    public = companies[_is_true(companies["is_public"]) & companies["ticker"].notna()]
    currency = public["currency"] if "currency" in public.columns else "USD"
    equity_rows = pd.DataFrame({
        "market_id": public["ticker"],
        "asset_type": "equity",
        "name": public["company_name"],
        "company_id": public["company_id"],
        "fund_id": pd.NA,
        "crypto_asset_id": pd.NA,
        "symbol": public["ticker"],
        "currency": currency,
        "exchange": public["exchange"],
    })

    funds = load_funds()
    fund_rows = pd.DataFrame({
        "market_id": funds["ticker"],
        "asset_type": funds["asset_class"],
        "name": funds["fund_name"],
        "company_id": pd.NA,
        "fund_id": funds["fund_id"],
        "crypto_asset_id": pd.NA,
        "symbol": funds["symbol"],
        "currency": funds["currency"],
        "exchange": funds["exchange"],
    })

    crypto = load_crypto_assets()
    # Coins without a Yahoo symbol that matches CoinCodex's price keep their
    # bare symbol; ingestion then prices them from CoinCodex (see run_ingestion).
    yf_symbol = crypto["yf_symbol"] if "yf_symbol" in crypto.columns else crypto["symbol"] + "-USD"
    crypto_rows = pd.DataFrame({
        "market_id": crypto["symbol"],
        "asset_type": "crypto",
        "name": crypto["asset_name"],
        "company_id": pd.NA,
        "fund_id": pd.NA,
        "crypto_asset_id": crypto["asset_id"],
        "symbol": yf_symbol.fillna(crypto["symbol"]),
        "currency": "USD",
        "exchange": pd.NA,
    })

    universe = pd.concat([equity_rows, fund_rows, crypto_rows], ignore_index=True)
    duplicates = universe[universe["market_id"].duplicated(keep=False)]
    if not duplicates.empty:
        raise ValueError(f"Duplicate market_id in universe:\n{duplicates}")
    return universe


def market_categories(universe: pd.DataFrame | None = None) -> dict[str, dict[str, list[str]]]:
    """{market_id: {"categories": [...], "segments": [...]}} for every tracked
    instrument. Stocks, benchmark funds and crypto get their asset-class
    category; any entity tagged in themes.csv also gets that theme, so e.g.
    Constellation Energy is in Stocks, AI Supply Chain and Energy at once."""
    universe = build_market_universe() if universe is None else universe
    funds = load_funds().set_index("fund_id")
    themes = load_themes()
    by_entity = themes.groupby("entity_id")

    out: dict[str, dict[str, list[str]]] = {}
    for row in universe.itertuples():
        cats: list[str] = []
        segments: list[str] = []
        if row.asset_type == "equity":
            cats.append(STOCKS)
        elif row.asset_type == "crypto":
            cats.append(CRYPTO)
        elif pd.notna(row.fund_id) and funds.at[row.fund_id, "role"] == "benchmark":
            cats.append(BENCHMARKS)
        entity = row.company_id if pd.notna(row.company_id) else row.fund_id
        if pd.notna(entity) and entity in by_entity.groups:
            tagged = by_entity.get_group(entity)
            cats.extend(tagged["theme"])
            segments.extend(f"{t} / {s}" for t, s in zip(tagged["theme"], tagged["segment"]))
        order = {c: i for i, c in enumerate(CATEGORY_ORDER)}
        out[row.market_id] = {
            "categories": sorted(set(cats), key=lambda c: order.get(c, len(order))),
            "segments": list(dict.fromkeys(segments)),
        }
    return out


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
