import numpy as np
import pandas as pd

from src.analytics.market_stats import add_drawdown, add_returns, add_rolling_volatility, compute_market_stats, summary_stats
from src.analytics.relationships import merge_sentiment_and_market, sentiment_return_correlation
from src.analytics.sentiment_stats import daily_sentiment, label_distribution


def _price_df(n=40, start_price=100.0, daily_growth=0.01, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    prices = [start_price]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + daily_growth + rng.normal(0, 0.01)))
    return pd.DataFrame({"date": dates, "close": prices})


class TestMarketStats:
    def test_returns_are_causal_only(self):
        df = add_returns(_price_df())
        # First row must be NaN (no prior day to compute a return from) — this
        # is the guard against accidental look-ahead in this module.
        assert pd.isna(df["return_1d"].iloc[0])
        assert df["return_1d"].iloc[1:].notna().all()

    def test_rolling_volatility_uses_only_past_window(self):
        df = add_returns(_price_df())
        df = add_rolling_volatility(df, windows=(5,))
        assert df["rolling_vol_5d"].iloc[:4].isna().all()
        assert df["rolling_vol_5d"].iloc[5:].notna().all()

    def test_drawdown_is_zero_at_new_highs(self):
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "close": [100, 110, 120]})
        df = add_drawdown(df)
        assert (df["drawdown"] == 0).all()  # monotonically increasing series never draws down

    def test_drawdown_negative_after_decline(self):
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "close": [100, 120, 90]})
        df = add_drawdown(df)
        assert df["drawdown"].iloc[2] < 0
        assert np.isclose(df["drawdown"].iloc[2], 90 / 120 - 1)

    def test_summary_stats_keys_present(self):
        df = compute_market_stats(_price_df())
        stats = summary_stats(df)
        for key in ["n_days", "start_date", "end_date", "mean_daily_return",
                    "annualized_volatility", "max_drawdown", "total_return"]:
            assert key in stats


class TestSentimentStats:
    def test_daily_sentiment_aggregates_correctly(self):
        sentiment_df = pd.DataFrame({
            "news_id": ["a", "b", "c"],
            "sentiment_model": ["vader"] * 3,
            "sentiment_score": [0.5, -0.5, 0.0],
            "sentiment_label": ["Bullish", "Bearish", "Neutral"],
        })
        news_df = pd.DataFrame({
            "news_id": ["a", "b", "c"],
            "timestamp": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"]),
            "matched_company_id": ["x", "x", "x"],
            "matched_asset_id": [None, None, None],
        })
        result = daily_sentiment(sentiment_df, news_df)
        assert len(result) == 2
        day1 = result[result["date"] == pd.Timestamp("2024-01-01").date()].iloc[0]
        assert day1["news_volume"] == 2
        assert np.isclose(day1["mean_sentiment"], 0.0)

    def test_label_distribution_counts(self):
        sentiment_df = pd.DataFrame({
            "sentiment_model": ["vader", "vader", "textblob"],
            "sentiment_label": ["Bullish", "Bullish", "Bearish"],
        })
        dist = label_distribution(sentiment_df, "vader")
        assert dist["Bullish"] == 2


class TestRelationships:
    def test_correlation_flags_insufficient_data(self):
        merged = pd.DataFrame({"mean_sentiment": [0.1], "return_1d": [0.01]})
        result = sentiment_return_correlation(merged)
        assert "note" in result

    def test_merge_aligns_on_date(self):
        sent = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3), "mean_sentiment": [0.1, 0.2, 0.3]})
        mkt = pd.DataFrame({"date": pd.date_range("2024-01-02", periods=3), "return_1d": [0.01, 0.02, 0.03]})
        merged = merge_sentiment_and_market(sent, mkt)
        assert len(merged) == 2  # only overlapping dates survive an inner join
