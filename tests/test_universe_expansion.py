"""Dynamic crypto ranking, OHLC repair and news-based AI event detection.
Offline: CoinCodex and Yahoo are replaced by fakes."""
from datetime import date

import pandas as pd
import pytest

import src.ingestion.crypto_universe as cu
from src.analytics.event_detection import classify, deal_size, detect_events
from src.ingestion.base import ProviderError
from src.ingestion.standardize import repair_ohlc_bounds
from src.ingestion.validate import validate_market_prices

CANDIDATES = pd.DataFrame({
    "symbol": ["BTC", "ETH", "SOL", "USDT", "TON", "ZEC"],
    "asset_name": ["Bitcoin", "Ethereum", "Solana", "Tether", "Toncoin", "Zcash"],
    "category": ["L1", "L1", "L1", "Stablecoin", "L1", "Privacy"],
    "pinned": [True, True, True, False, False, False],
})
CAPS = {"BTC": (1_700e9, 84_000.0), "ETH": (330e9, 2_700.0), "USDT": (180e9, 1.0),
        "TON": (5e9, 2.0), "ZEC": (28e9, 1_650.0), "SOL": (1e9, 120.0)}


class TestCryptoRanking:
    def test_top_n_plus_pinned_assets(self):
        ranked = pd.DataFrame([{"symbol": s, "asset_name": s, "market_cap_usd": c, "price_usd": p}
                               for s, (c, p) in CAPS.items()])
        chosen = cu.select_universe(ranked, CANDIDATES, top_n=3).set_index("symbol")
        assert chosen.index.tolist() == ["BTC", "ETH", "USDT", "SOL"]  # SOL is pinned, ranked 6th
        assert chosen.loc["SOL", "rank"] == 6
        assert chosen.loc["USDT", "asset_name"] == "Tether"

    def test_yahoo_symbol_only_trusted_when_prices_agree(self):
        # Yahoo's TON-USD is a different coin trading near $0.005
        closes = {"BTC-USD": 84_100.0, "TON-USD": 0.005}
        assert cu.trusted_yahoo_symbol("BTC", 84_000.0, closes.get) == "BTC-USD"
        assert cu.trusted_yahoo_symbol("TON", 2.0, closes.get) is None
        assert cu.trusted_yahoo_symbol("NEW", 1.0, closes.get) is None

    def test_falls_back_to_ranking_candidates_when_listing_is_down(self, monkeypatch):
        def listing_down():
            raise ProviderError("coincodex: HTTP 503")
        monkeypatch.setattr(cu, "fetch_listing", listing_down)
        monkeypatch.setattr(cu, "load_candidates", lambda: CANDIDATES)
        monkeypatch.setattr(cu, "fetch_latest_cap", lambda s, today=None: CAPS.get(s))
        closes = {"BTC-USD": 84_000.0, "ETH-USD": 2_700.0}
        out = cu.refresh_crypto_universe(top_n=2, today=date(2026, 9, 27), write=False,
                                         last_close=closes.get).set_index("symbol")
        assert out.index.tolist() == ["BTC", "ETH", "SOL"]
        assert set(out["rank_source"]) == {"coincodex_history"}
        assert out.loc["BTC", "yf_symbol"] == "BTC-USD" and pd.isna(out.loc["SOL", "yf_symbol"])

    def test_no_market_caps_at_all_is_an_error(self, monkeypatch):
        monkeypatch.setattr(cu, "fetch_latest_cap", lambda s, today=None: None)
        with pytest.raises(ProviderError):
            cu.rank_candidates(CANDIDATES)


def test_ohlc_repair_makes_glitched_rows_valid():
    df = pd.DataFrame({"date": pd.date_range("2024-10-14", periods=2), "open": [59500.0, 10.0],
                       "high": [61200.0, 11.0], "low": [59400.0, 9.0], "close": [59300.0, 10.5],
                       "volume": [1, 1]})
    assert not validate_market_prices(df, "X").passed
    fixed, n = repair_ohlc_bounds(df)
    assert n == 1 and validate_market_prices(fixed, "X").passed
    assert fixed.loc[0, "low"] == 59300.0
    pd.testing.assert_series_equal(fixed.loc[1], df.loc[1])


class TestEventDetection:
    @pytest.mark.parametrize("title, expected", [
        ("Anthropic Introduces Claude Opus 5", ("model_release", "opus 5")),
        ("OpenAI Has Launched GPT-6 Astra", ("model_release", "gpt-6")),
        ("Amazon, OpenAI Sign $38B Deal For Nvidia GPU Access", ("partnership", "amazon:38b")),
        ("Nvidia acquires Hugging Face in $12.9 billion deal", ("acquisition", "nvidia:12.9b")),
        ("Alibaba Unveils AI Chip to Drive 20GW of Data Centers", ("hardware", "alibaba")),
    ])
    def test_classifies_ai_events(self, title, expected):
        assert classify(title) == expected

    @pytest.mark.parametrize("title", [
        "Is Nvidia Stock a Buy After Its Latest Chip Launch?",            # stock commentary
        "Redwood Family Wealth LLC Buys New Position in NVIDIA $NVDA",    # holdings filing
        "Microsoft expands data center holdings. It spent $38 million",   # not material
        "Cadence Unveils Virtual Engineer for Chip Design, powered by NVIDIA",  # NVIDIA isn't the actor
    ])
    def test_ignores_noise(self, title):
        assert classify(title) is None

    def test_deal_size_normalises_units(self):
        assert deal_size("a $38 billion deal") == "38b"
        assert deal_size("raises $1.5bn") == "1.5b"
        assert deal_size("a 10GW build-out") == "10gw"
        assert deal_size("spent $38 million") is None

    def test_groups_bursts_and_drops_curated_duplicates(self):
        ts = pd.to_datetime(["2026-07-24 10:00", "2026-07-24 12:00", "2026-07-25 09:00",
                             "2026-09-04 10:00", "2026-09-04 11:00", "2026-09-30 10:00"])
        news = pd.DataFrame({"timestamp": ts, "title": [
            "Anthropic Introduces Claude Opus 5", "Anthropic launches Claude Opus 5 model",
            "Claude Opus 5 now available on AWS", "OpenAI Has Launched GPT-6 Astra",
            "OpenAI releases GPT-6 to all users", "Anthropic Introduces Claude Opus 5 in Europe"]})
        curated = pd.DataFrame({"event_date": ["2026-09-04"], "organisation": ["openai"],
                                "title": ["GPT-6 Astra launch (OpenAI)"]})
        out = detect_events(news, curated)
        # Opus 5: one 3-article burst (the late single article forms its own, too-small
        # burst); GPT-6 is already in the curated catalogue.
        assert out["event_id"].tolist() == ["news_model_release_opus_5_20260724"]
        assert out.loc[0, "n_articles"] == 3 and out.loc[0, "primary_market_id"] == "AMZN"
