"""Dynamic crypto universe: the top-N cryptocurrencies by market cap, ranked
from CoinCodex, plus any pinned assets (the ones the models are trained on).

Ranking source, in order:
1. CoinCodex's full coin listing (every listed coin, so the ranking is open-ended).
2. If that endpoint is unavailable (it was returning Cloudflare 5xx errors when
   this was written), CoinCodex's per-coin history endpoint, which reports each
   coin's market cap, queried for every coin in crypto_candidates.csv. The
   candidate pool is deliberately much larger than N, so it only has to
   contain the top N, not predict it.

Prices are then fetched through yfinance where possible. A Yahoo symbol is
only trusted if its latest close agrees with CoinCodex's price: Yahoo reuses
tickers such as TON-USD and WLFI-USD for unrelated coins. Coins without a
trusted Yahoo symbol are priced from CoinCodex directly.

The result is written to data/reference/crypto_assets.csv, which the rest of
the pipeline reads. If CoinCodex is unreachable the existing file is kept.
Run as: python -m src.ingestion.crypto_universe
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd

from src.config import REFERENCE_DIR
from src.ingestion.base import ProviderError
from src.ingestion.providers import get_json

logger = logging.getLogger(__name__)

TOP_N = 10
LISTING_URL = "https://coincodex.com/apps/coincodex/cache/all_coins.json"
HISTORY_URL = "https://coincodex.com/api/coincodex/get_coin_history"
PRICE_TOLERANCE = 0.05  # max relative gap between Yahoo's and CoinCodex's latest price
CANDIDATES_PATH = REFERENCE_DIR / "crypto_candidates.csv"
ASSETS_PATH = REFERENCE_DIR / "crypto_assets.csv"

ASSET_COLUMNS = ["asset_id", "asset_name", "symbol", "yf_symbol", "category", "rank",
                 "market_cap_usd", "price_usd", "pinned", "as_of", "rank_source"]


def load_candidates() -> pd.DataFrame:
    df = pd.read_csv(CANDIDATES_PATH)
    df["pinned"] = df["pinned"].astype(str).str.lower() == "true"
    return df


def fetch_listing() -> pd.DataFrame:
    """Every coin CoinCodex lists: symbol, asset_name, market_cap_usd, price_usd."""
    payload = get_json(LISTING_URL, provider="coincodex", timeout=60)
    rows = payload if isinstance(payload, list) else payload.get("data", [])
    df = pd.DataFrame(rows)
    if df.empty or "symbol" not in df.columns or "market_cap_usd" not in df.columns:
        raise ProviderError("coincodex: listing has no symbol/market_cap_usd columns")
    return pd.DataFrame({
        "symbol": df["symbol"].astype(str).str.upper(),
        "asset_name": df.get("name", df["symbol"]),
        "market_cap_usd": pd.to_numeric(df["market_cap_usd"], errors="coerce"),
        "price_usd": pd.to_numeric(df.get("last_price_usd"), errors="coerce"),
    }).dropna(subset=["market_cap_usd"])


def fetch_latest_cap(symbol: str, today: date | None = None) -> tuple[float, float] | None:
    """(market_cap_usd, price_usd) from the last few days of CoinCodex history."""
    end = today or date.today()
    start = end - timedelta(days=4)
    try:
        payload = get_json(f"{HISTORY_URL}/{symbol}/{start}/{end}/5", provider="coincodex", timeout=60)
    except ProviderError as exc:
        logger.warning("coincodex history failed for %s: %s", symbol, exc)
        return None
    rows = [r for r in (payload.get(symbol) or []) if len(r) >= 4 and r[3]]
    if not rows:
        return None
    return float(rows[-1][3]), float(rows[-1][1])


def rank_candidates(candidates: pd.DataFrame, today: date | None = None) -> pd.DataFrame:
    rows = []
    for c in candidates.itertuples():
        latest = fetch_latest_cap(c.symbol, today)
        if latest:
            rows.append({"symbol": c.symbol, "asset_name": c.asset_name,
                         "market_cap_usd": latest[0], "price_usd": latest[1]})
    if not rows:
        raise ProviderError("coincodex: no market caps returned for any candidate")
    return pd.DataFrame(rows)


def yahoo_last_close(yf_symbol: str) -> float | None:
    import yfinance as yf

    import src.config  # noqa: F401 - CA bundle for curl_cffi
    try:
        hist = yf.Ticker(yf_symbol).history(period="5d")
    except Exception:  # noqa: BLE001 - unknown symbol raises various errors
        return None
    return float(hist["Close"].iloc[-1]) if len(hist) else None


def trusted_yahoo_symbol(symbol: str, reference_price: float | None,
                         last_close=yahoo_last_close) -> str | None:
    """SYMBOL-USD if Yahoo's latest close is within PRICE_TOLERANCE of CoinCodex's."""
    if not reference_price:
        return None
    candidate = f"{symbol}-USD"
    close = last_close(candidate)
    if close is None or abs(close / reference_price - 1) > PRICE_TOLERANCE:
        logger.info("not using %s: Yahoo close %s vs CoinCodex %s", candidate, close, reference_price)
        return None
    return candidate


def select_universe(ranked: pd.DataFrame, candidates: pd.DataFrame, top_n: int = TOP_N) -> pd.DataFrame:
    """Top `top_n` by market cap, plus pinned candidates, with 1-based rank."""
    ranked = ranked.sort_values("market_cap_usd", ascending=False).drop_duplicates("symbol").reset_index(drop=True)
    ranked["rank"] = ranked.index + 1
    pinned = set(candidates.loc[candidates["pinned"], "symbol"])
    chosen = ranked[(ranked["rank"] <= top_n) | ranked["symbol"].isin(pinned)].copy()
    meta = candidates.set_index("symbol")
    chosen["pinned"] = chosen["symbol"].isin(pinned)
    chosen["category"] = chosen["symbol"].map(meta["category"]) if len(meta) else None
    known_names = chosen["symbol"].map(meta["asset_name"]) if len(meta) else chosen["asset_name"]
    chosen["asset_name"] = known_names.fillna(chosen["asset_name"])
    chosen["asset_id"] = chosen["symbol"].str.lower()
    return chosen


def refresh_crypto_universe(top_n: int = TOP_N, today: date | None = None, write: bool = True,
                            last_close=yahoo_last_close) -> pd.DataFrame:
    candidates = load_candidates()
    try:
        ranked, source = fetch_listing(), "coincodex_listing"
    except ProviderError as exc:
        logger.warning("coincodex listing unavailable (%s); ranking the candidate pool instead",
                       str(exc).splitlines()[0])
        ranked, source = rank_candidates(candidates, today), "coincodex_history"
    chosen = select_universe(ranked, candidates, top_n)
    chosen["yf_symbol"] = [trusted_yahoo_symbol(s, p, last_close) for s, p in zip(chosen["symbol"], chosen["price_usd"])]
    chosen["as_of"] = (today or date.today()).isoformat()
    chosen["rank_source"] = source
    out = chosen[ASSET_COLUMNS].sort_values("rank").reset_index(drop=True)
    if write:
        out.to_csv(ASSETS_PATH, index=False, lineterminator="\n")
    return out


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    out = refresh_crypto_universe()
    logger.info("crypto universe (%s):\n%s", out["rank_source"].iloc[0],
                out[["rank", "symbol", "asset_name", "market_cap_usd", "yf_symbol", "pinned"]].to_string(index=False))


if __name__ == "__main__":
    main()
