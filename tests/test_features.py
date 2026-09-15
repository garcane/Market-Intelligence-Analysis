import numpy as np
import pandas as pd

from src.features.cross_sectional_features import (
    add_cross_sectional_features,
    build_returns_wide,
    compute_ai_index_return,
    compute_market_return,
    compute_sector_returns,
)
from src.features.market_features import (
    add_lagged_returns,
    add_moving_averages,
    add_rolling_returns,
    add_rsi,
    add_volume_features,
    build_market_features,
)
from src.features.sentiment_features import build_sentiment_features
from src.features.validate import validate_features


def _price_df(n=120, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = 100 * np.cumprod(1 + rng.normal(0.0005, 0.02, n))
    high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
    open_ = close * (1 + rng.normal(0, 0.003, n))
    volume = rng.integers(1_000_000, 5_000_000, n).astype(float)
    return pd.DataFrame({"date": dates, "open": open_, "high": high, "low": low,
                          "close": close, "volume": volume})


class TestLeakageSafety:
    """The central acceptance criterion for this stage (Rule 4): a feature
    value at row t must never change when data after t is mutated."""

    def test_market_features_unaffected_by_future_mutation(self):
        df = _price_df()
        features_before = build_market_features(df)

        mutated = df.copy()
        cutoff = 60
        # violently change every row after the cutoff
        mutated.loc[cutoff + 1:, "close"] *= 5.0
        mutated.loc[cutoff + 1:, "volume"] *= 10.0
        features_after = build_market_features(mutated)

        feature_cols = [c for c in features_before.columns if c not in ("date", "open", "high", "low", "close", "volume")]
        for col in feature_cols:
            before = features_before[col].iloc[:cutoff]
            after = features_after[col].iloc[:cutoff]
            pd.testing.assert_series_equal(before, after, check_names=False,
                                            obj=f"leakage detected in column '{col}'")

    def test_rolling_returns_are_backward_looking(self):
        df = _price_df()
        result = add_rolling_returns(df, windows=(5,))
        # first 5 rows must be NaN (nothing 5 days back exists yet)
        assert result["rolling_return_5d"].iloc[:5].isna().all()

    def test_lagged_returns_shift_correctly(self):
        df = _price_df()
        from src.analytics.market_stats import add_returns
        df = add_returns(df)
        result = add_lagged_returns(df, lags=(1,))
        # lag_return_1d at row i must equal return_1d at row i-1
        assert np.allclose(
            result["lag_return_1d"].iloc[10:].values,
            result["return_1d"].iloc[9:-1].values,
        )

    def test_moving_average_matches_manual_calculation(self):
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10),
                            "close": [float(i) for i in range(1, 11)]})
        result = add_moving_averages(df, windows=(3,))
        # SMA_3 at row 4 (0-indexed) = mean(close[2:5]) = mean(3,4,5) = 4
        assert result["sma_3d"].iloc[4] == 4.0
        assert result["sma_3d"].iloc[:2].isna().all()

    def test_rsi_is_100_for_pure_uptrend(self):
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=30),
                            "close": np.linspace(100, 200, 30)})
        result = add_rsi(df, window=14)
        # a monotonic uptrend has zero losses -> RSI = 100 once the window fills
        assert (result["rsi_14d"].iloc[15:] == 100.0).all()

    def test_rsi_bounded_between_0_and_100(self):
        df = _price_df()
        result = add_rsi(df)
        valid = result["rsi_14d"].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_volume_features_no_lookahead(self):
        df = _price_df()
        result = add_volume_features(df, window=5)
        assert result["volume_change_1d"].iloc[0] != result["volume_change_1d"].iloc[0]  # NaN check


class TestCrossSectional:
    def test_market_return_is_mean_of_all_assets(self):
        wide = pd.DataFrame({
            "A": [0.01, 0.02, -0.01],
            "B": [0.03, -0.02, 0.01],
        }, index=pd.date_range("2024-01-01", periods=3))
        result = compute_market_return(wide)
        assert np.isclose(result.iloc[0], 0.02)

    def test_ai_index_excludes_non_equity_assets(self):
        wide = pd.DataFrame({
            "NVDA": [0.05], "MSFT": [0.03], "BTC": [0.50],
        }, index=pd.date_range("2024-01-01", periods=1))
        result = compute_ai_index_return(wide, equity_market_ids=["NVDA", "MSFT"])
        assert np.isclose(result.iloc[0], 0.04)  # excludes BTC's 0.50

    def test_relative_performance_is_asset_minus_benchmark(self):
        asset_df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=2), "return_1d": [0.05, 0.02]})
        market_return = pd.Series([0.02, 0.02], index=asset_df["date"], name="market_return")
        ai_index_return = pd.Series([0.03, 0.03], index=asset_df["date"], name="ai_index_return")
        result = add_cross_sectional_features(asset_df, market_return, ai_index_return)
        assert np.isclose(result["relative_performance"].iloc[0], 0.03)

    def test_sector_returns_only_include_sector_members(self):
        wide = pd.DataFrame({
            "NVDA": [0.05], "AMD": [0.03], "MSFT": [0.10],
        }, index=pd.date_range("2024-01-01", periods=1))
        result = compute_sector_returns(wide, {"Compute": ["NVDA", "AMD"]})
        assert np.isclose(result["Compute"].iloc[0], 0.04)


class TestSentimentFeatures:
    def test_no_news_days_get_zero_volume_not_fabricated_sentiment(self):
        sentiment_df = pd.DataFrame(columns=["news_id", "sentiment_model", "sentiment_score", "sentiment_label"])
        news_df = pd.DataFrame(columns=["news_id", "timestamp", "matched_company_id", "matched_asset_id"])
        date_index = pd.date_range("2024-01-01", periods=5)
        result = build_sentiment_features("nvidia", sentiment_df, news_df, date_index)
        assert (result["news_volume"] == 0).all()
        assert result["sentiment_current"].isna().all()  # NaN, not 0 — no fabricated neutral signal

    def test_sentiment_features_joined_on_correct_dates(self):
        sentiment_df = pd.DataFrame({
            "news_id": ["a", "b"], "sentiment_model": ["vader", "vader"],
            "sentiment_score": [0.5, -0.5], "sentiment_label": ["Bullish", "Bearish"],
        })
        news_df = pd.DataFrame({
            "news_id": ["a", "b"],
            "timestamp": pd.to_datetime(["2024-01-02", "2024-01-04"]),
            "matched_company_id": ["nvidia", "nvidia"],
            "matched_asset_id": [None, None],
        })
        date_index = pd.date_range("2024-01-01", periods=5)
        result = build_sentiment_features("nvidia", sentiment_df, news_df, date_index)
        jan2 = result[result["date"] == pd.Timestamp("2024-01-02")].iloc[0]
        jan1 = result[result["date"] == pd.Timestamp("2024-01-01")].iloc[0]
        assert np.isclose(jan2["sentiment_current"], 0.5)
        assert jan1["news_volume"] == 0
        assert pd.isna(jan1["sentiment_current"])

    def test_lagged_sentiment_does_not_leak_future_news(self):
        sentiment_df = pd.DataFrame({
            "news_id": ["a"], "sentiment_model": ["vader"],
            "sentiment_score": [0.9], "sentiment_label": ["Bullish"],
        })
        news_df = pd.DataFrame({
            "news_id": ["a"], "timestamp": pd.to_datetime(["2024-01-05"]),
            "matched_company_id": ["nvidia"], "matched_asset_id": [None],
        })
        date_index = pd.date_range("2024-01-01", periods=10)
        result = build_sentiment_features("nvidia", sentiment_df, news_df, date_index)
        # the news on 2024-01-05 must not appear in lag_sentiment_1d before that date
        before = result[result["date"] < pd.Timestamp("2024-01-05")]
        assert before["lag_sentiment_1d"].isna().all()


class TestValidate:
    def test_valid_features_pass(self):
        df = pd.DataFrame({
            "market_id": ["A", "A", "B"],
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-01"]),
            "return_1d": [np.nan, 0.01, np.nan],
            "log_return_1d": [np.nan, 0.01, np.nan],
        })
        result = validate_features(df)
        assert result.passed

    def test_duplicate_market_date_flagged(self):
        df = pd.DataFrame({
            "market_id": ["A", "A"],
            "date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
            "return_1d": [np.nan, 0.01],
            "log_return_1d": [np.nan, 0.01],
        })
        result = validate_features(df)
        assert not result.passed
        assert any("duplicate" in i for i in result.issues)
