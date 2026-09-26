"""Offline tests for the resumable news backfill."""
import json
from datetime import date, timedelta

import pandas as pd
import pytest

from src.ingestion.base import HistoricalNewsProvider, ProviderError, QuotaExhausted
from src.ingestion.news_backfill import cache_path, coverage_report, merge_backfill, plan_windows, run_backfill
from src.ingestion.standardize import merge_news_frames

NO_SLEEP = {"sleep": lambda s: None}
MARKETS = [("NVDA", "equity"), ("BTC", "crypto")]


class FakeProvider(HistoricalNewsProvider):
    """Returns Finnhub-shaped payloads; can fail on a given call number."""
    name = "finnhub"  # reuse the real parser in merge_backfill
    window_days = 7
    daily_request_budget = None
    min_interval_seconds = 0.0

    def __init__(self, fail_on=None, error=QuotaExhausted, equities_only=True):
        self.calls = []
        self.fail_on = fail_on or set()
        self.error = error
        self.equities_only = equities_only

    def provider_symbol(self, market_id, asset_type):
        return None if (self.equities_only and asset_type != "equity") else market_id

    def fetch_window_raw(self, symbol, start, end):
        self.calls.append((symbol, start))
        if len(self.calls) in self.fail_on:
            raise self.error("stubbed failure")
        ts = int(pd.Timestamp(end).timestamp())
        return [{"id": f"{symbol}-{start}", "datetime": ts, "headline": f"{symbol} news",
                 "url": f"https://x/{symbol}/{start}"}]

    @staticmethod
    def parse_window(raw):
        from src.ingestion.providers import FinnhubNewsProvider
        return FinnhubNewsProvider.parse_window(raw)


def test_plan_windows_newest_first_contiguous_and_clipped():
    windows = plan_windows(date(2024, 1, 31), date(2024, 1, 10), window_days=7)
    assert windows[0] == (date(2024, 1, 25), date(2024, 1, 31))
    assert windows[-1] == (date(2024, 1, 10), date(2024, 1, 10))  # clipped at earliest
    for (start, _), (_, prev_end) in zip(windows, windows[1:]):
        assert prev_end == start - timedelta(days=1)  # no gaps, no overlap


def test_backfill_caches_and_second_run_makes_no_calls(tmp_path):
    provider = FakeProvider()
    kwargs = dict(latest=date(2024, 1, 31), earliest=date(2024, 1, 1), cache_root=tmp_path, **NO_SLEEP)
    run_backfill([provider], MARKETS, **kwargs)
    first = len(provider.calls)
    assert first == len(plan_windows(date(2024, 1, 31), date(2024, 1, 1), 7))  # NVDA only; BTC unsupported
    summary = run_backfill([provider], MARKETS, **kwargs)
    assert len(provider.calls) == first
    assert summary["finnhub"]["cached_skipped"] == first


def test_quota_stop_keeps_progress_and_resumes_next_day(tmp_path):
    kwargs = dict(latest=date(2024, 1, 31), earliest=date(2024, 1, 1), cache_root=tmp_path, **NO_SLEEP)
    provider = FakeProvider(fail_on={3})
    summary = run_backfill([provider], MARKETS, **kwargs)
    assert "quota exhausted" in summary["finnhub"]["stopped"]
    assert summary["finnhub"]["fetched"] == 2

    same_day = FakeProvider()
    run_backfill([same_day], MARKETS, **kwargs)
    assert same_day.calls == []  # stopped for today

    state_path = tmp_path / "_state.json"
    state = json.loads(state_path.read_text())
    state["finnhub"]["date"] = "2000-01-01"  # simulate tomorrow
    state_path.write_text(json.dumps(state))
    next_day = FakeProvider()
    run_backfill([next_day], MARKETS, **kwargs)
    fetched_before = {("NVDA", "2024-01-31"), ("NVDA", "2024-01-24")}
    assert not fetched_before & {(s, str(pd.Timestamp(st).date() + timedelta(days=6))) for s, st in next_day.calls}
    assert len(next_day.calls) == len(plan_windows(date(2024, 1, 31), date(2024, 1, 1), 7)) - 2


def test_history_limit_skips_windows_the_plan_cannot_serve(tmp_path):
    provider = FakeProvider()
    provider.history_limit_days = 10
    today = date.today()
    run_backfill([provider], MARKETS, latest=today, earliest=today - timedelta(days=100),
                 cache_root=tmp_path, **NO_SLEEP)
    assert len(provider.calls) == 2  # only the two 7-day windows inside the 10-day limit
    oldest = min(pd.Timestamp(start).date() for _, start in provider.calls)
    assert oldest >= today - timedelta(days=10)


def test_daily_budget_is_respected(tmp_path):
    provider = FakeProvider()
    provider.daily_request_budget = 2
    summary = run_backfill([provider], MARKETS, latest=date(2024, 1, 31), earliest=date(2024, 1, 1),
                           cache_root=tmp_path, **NO_SLEEP)
    assert len(provider.calls) == 2
    assert "daily budget" in summary["finnhub"]["stopped"]


def test_failed_request_is_not_cached(tmp_path):
    provider = FakeProvider(fail_on={1}, error=ProviderError)
    summary = run_backfill([provider], MARKETS, latest=date(2024, 1, 31), earliest=date(2024, 1, 25),
                           cache_root=tmp_path, **NO_SLEEP)
    assert summary["finnhub"]["failed"] == 1
    assert not cache_path(tmp_path, "finnhub", "NVDA", date(2024, 1, 25)).exists()


def test_max_requests_caps_the_run(tmp_path):
    provider = FakeProvider(equities_only=False)
    run_backfill([provider], MARKETS, latest=date(2024, 1, 31), earliest=date(2024, 1, 1),
                 max_requests=3, cache_root=tmp_path, **NO_SLEEP)
    assert len(provider.calls) == 3


def test_merge_attributes_articles_to_queried_market_and_dedupes(tmp_path):
    provider = FakeProvider(equities_only=False)
    run_backfill([provider], MARKETS, latest=date(2024, 1, 31), earliest=date(2024, 1, 25),
                 cache_root=tmp_path, **NO_SLEEP)
    # an extra cached window repeating an existing url
    dup = cache_path(tmp_path, "finnhub", "NVDA", date(2023, 1, 1))
    dup.parent.mkdir(parents=True, exist_ok=True)
    dup.write_text(json.dumps({"provider": "finnhub", "market_id": "NVDA", "raw": [
        {"id": "d", "datetime": 1706000000, "headline": "dup", "url": "https://x/NVDA/2024-01-25"}]}))

    entity_by_market = {"NVDA": ("nvidia", "equity"), "BTC": ("btc", "crypto")}
    df = merge_backfill(tmp_path, entity_by_market)
    assert df["url"].is_unique
    nvda = df[df["entity"] == "NVDA"].iloc[0]
    btc = df[df["entity"] == "BTC"].iloc[0]
    assert nvda["matched_company_id"] == "nvidia" and nvda["matched_asset_id"] is None
    assert btc["matched_asset_id"] == "btc" and btc["matched_company_id"] is None
    assert {"news_id", "timestamp", "source_id"} <= set(df.columns)


def test_merge_news_frames_keeps_existing_row_on_duplicate_url():
    existing = pd.DataFrame({"news_id": ["old"], "url": ["u1"], "timestamp": pd.to_datetime(["2024-01-02"])})
    new = pd.DataFrame({"news_id": ["new", "n2"], "url": ["u1", "u2"],
                        "timestamp": pd.to_datetime(["2024-01-02", "2024-01-01"])})
    merged = merge_news_frames(existing, new)
    assert merged["news_id"].tolist() == ["n2", "old"]  # sorted by time; existing id kept


def test_coverage_report_by_period_counts_exact_trading_days():
    trading = pd.Series(pd.to_datetime(["2024-01-02", "2024-01-03", "2024-02-01", "2024-03-01"]))
    news = pd.DataFrame({
        "timestamp": pd.to_datetime(["2024-01-02 09:00", "2024-01-06 12:00", "2024-03-01 18:00"]),  # 01-06 is a Saturday
        "matched_company_id": ["nvidia", "nvidia", "nvidia"],
        "matched_asset_id": [None, None, None],
    })
    report = coverage_report(news, {"NVDA": trading}, {"NVDA": ("nvidia", "equity")},
                             train_end="2024-01-31", val_end="2024-02-15")
    m = report["by_market"]["NVDA"]
    assert m["train"] == {"days": 2, "covered": 1, "pct": 0.5}
    assert m["validation"] == {"days": 1, "covered": 0, "pct": 0.0}
    assert m["test"] == {"days": 1, "covered": 1, "pct": 1.0}
    assert report["totals"]["train"]["pct"] == 0.5
