"""Tests for ingestion validation and storage. No network calls — uses
synthetic DataFrames so these run offline and deterministically."""
import pandas as pd
import pytest

from src.ingestion.store import round_trip_matches
from src.ingestion.universe import build_market_universe
from src.ingestion.validate import validate_market_prices, validate_news


def _good_prices_df():
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=5, freq="D"),
        "open": [10.0, 11.0, 12.0, 13.0, 14.0],
        "high": [11.0, 12.0, 13.0, 14.0, 15.0],
        "low": [9.0, 10.0, 11.0, 12.0, 13.0],
        "close": [10.5, 11.5, 12.5, 13.5, 14.5],
        "volume": [100, 200, 300, 400, 500],
    })


class TestValidateMarketPrices:
    def test_valid_data_passes(self):
        result = validate_market_prices(_good_prices_df(), "TEST")
        assert result.passed
        assert result.issues == []
        assert result.row_count == 5

    def test_missing_columns_fails(self):
        df = _good_prices_df().drop(columns=["volume"])
        result = validate_market_prices(df, "TEST")
        assert not result.passed
        assert any("missing required columns" in i for i in result.issues)

    def test_empty_dataframe_fails(self):
        df = _good_prices_df().iloc[0:0]
        result = validate_market_prices(df, "TEST")
        assert not result.passed
        assert any("zero rows" in i for i in result.issues)

    def test_duplicate_dates_flagged(self):
        df = _good_prices_df()
        df.loc[1, "date"] = df.loc[0, "date"]
        result = validate_market_prices(df, "TEST")
        assert not result.passed
        assert any("duplicate date" in i for i in result.issues)

    def test_null_values_flagged(self):
        df = _good_prices_df()
        df.loc[0, "close"] = None
        result = validate_market_prices(df, "TEST")
        assert not result.passed
        assert any("null value" in i for i in result.issues)

    def test_negative_volume_flagged(self):
        df = _good_prices_df()
        df.loc[0, "volume"] = -50
        result = validate_market_prices(df, "TEST")
        assert not result.passed
        assert any("negative volume" in i for i in result.issues)

    def test_zero_close_flagged(self):
        df = _good_prices_df()
        df.loc[0, "close"] = 0
        result = validate_market_prices(df, "TEST")
        assert not result.passed
        assert any("close <= 0" in i for i in result.issues)

    def test_high_below_low_flagged(self):
        df = _good_prices_df()
        df.loc[0, "high"] = 1.0
        df.loc[0, "low"] = 5.0
        result = validate_market_prices(df, "TEST")
        assert not result.passed
        assert any("high < low" in i for i in result.issues)

    def test_impossible_ohlc_flagged(self):
        # high below open/close should be caught even when high >= low
        df = _good_prices_df()
        df.loc[0, "open"] = 100.0
        result = validate_market_prices(df, "TEST")
        assert not result.passed
        assert any("high < open" in i for i in result.issues)


class TestValidateNews:
    def test_valid_news_passes(self):
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=3, freq="D"),
            "source_id": ["a", "b", "c"],
            "title": ["Headline 1", "Headline 2", "Headline 3"],
            "url": ["http://a", "http://b", "http://c"],
        })
        result = validate_news(df)
        assert result.passed

    def test_duplicate_urls_flagged(self):
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=2, freq="D"),
            "source_id": ["a", "b"],
            "title": ["Headline 1", "Headline 2"],
            "url": ["http://a", "http://a"],
        })
        result = validate_news(df)
        assert not result.passed
        assert any("duplicate url" in i for i in result.issues)

    def test_empty_title_flagged(self):
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=2, freq="D"),
            "source_id": ["a", "b"],
            "title": ["", "Headline 2"],
            "url": ["http://a", "http://b"],
        })
        result = validate_news(df)
        assert not result.passed
        assert any("empty title" in i for i in result.issues)


class TestRoundTrip:
    def test_round_trip_matches(self, tmp_path):
        df = _good_prices_df()
        path = tmp_path / "test.parquet"
        matches, issues = round_trip_matches(df, path)
        assert matches, issues
        assert path.exists()

    def test_round_trip_is_idempotent_when_run_twice(self, tmp_path):
        df = _good_prices_df()
        path = tmp_path / "test.parquet"
        matches1, _ = round_trip_matches(df, path)
        matches2, _ = round_trip_matches(df, path)
        assert matches1 and matches2

    def test_round_trip_tolerates_datetime_unit_change(self, tmp_path):
        # Regression test: yfinance returns datetime64[s]; parquet round-trips
        # can shift the stored unit (e.g. to ms), which must not be reported
        # as a data mismatch since the represented instant is unchanged.
        df = _good_prices_df()
        df["date"] = df["date"].astype("datetime64[s]")
        path = tmp_path / "test.parquet"
        matches, issues = round_trip_matches(df, path)
        assert matches, issues

    def test_round_trip_tolerates_all_null_object_column(self, tmp_path):
        # Regression test: a pd.NA-filled object column (e.g. market_cap for
        # equities) becomes None after a parquet round-trip; that must not be
        # reported as a mismatch since both represent "missing".
        df = _good_prices_df()
        df["market_cap"] = pd.array([pd.NA] * len(df), dtype="object")
        path = tmp_path / "test.parquet"
        matches, issues = round_trip_matches(df, path)
        assert matches, issues


class TestMarketUniverse:
    def test_universe_has_no_duplicate_market_ids(self):
        universe = build_market_universe()
        assert not universe["market_id"].duplicated().any()

    def test_universe_has_both_asset_types(self):
        universe = build_market_universe()
        assert set(universe["asset_type"]) == {"equity", "crypto"}

    def test_every_row_has_exactly_one_of_company_or_crypto_id(self):
        universe = build_market_universe()
        has_company = universe["company_id"].notna()
        has_crypto = universe["crypto_asset_id"].notna()
        assert (has_company ^ has_crypto).all()
