import numpy as np
import pandas as pd

from src.analytics.indices import (
    annualized_sharpe,
    beta,
    build_index_return,
    cumulative_return,
    index_summary,
    max_drawdown,
    rolling_correlation,
)


class TestBuildIndexReturn:
    def test_equal_weighted_mean(self):
        wide = pd.DataFrame({"A": [0.02, 0.04], "B": [0.04, 0.02], "C": [0.0, 0.0]})
        result = build_index_return(wide, ["A", "B"])
        assert np.allclose(result, [0.03, 0.03])

    def test_missing_members_are_skipped_not_erroring(self):
        wide = pd.DataFrame({"A": [0.02]})
        result = build_index_return(wide, ["A", "NOT_INGESTED"])
        assert np.isclose(result.iloc[0], 0.02)

    def test_raises_when_no_members_available(self):
        wide = pd.DataFrame({"A": [0.02]})
        try:
            build_index_return(wide, ["X", "Y"])
            assert False, "expected ValueError"
        except ValueError:
            pass


class TestRiskMetrics:
    def test_cumulative_return_compounds(self):
        returns = pd.Series([0.10, 0.10])
        result = cumulative_return(returns)
        assert np.isclose(result.iloc[-1], 1.1 * 1.1 - 1)

    def test_max_drawdown_zero_for_monotonic_gains(self):
        returns = pd.Series([0.01] * 10)
        assert max_drawdown(returns) == 0.0

    def test_max_drawdown_negative_after_decline(self):
        returns = pd.Series([0.10, -0.20, 0.0])
        dd = max_drawdown(returns)
        assert dd < 0

    def test_sharpe_nan_for_zero_variance(self):
        returns = pd.Series([0.01, 0.01, 0.01])
        assert np.isnan(annualized_sharpe(returns))

    def test_sharpe_positive_for_positive_trend(self):
        rng = np.random.default_rng(0)
        returns = pd.Series(rng.normal(0.001, 0.01, 500))
        assert annualized_sharpe(returns) > 0

    def test_beta_of_asset_against_itself_is_one(self):
        rng = np.random.default_rng(0)
        returns = pd.Series(rng.normal(0, 0.02, 200))
        assert np.isclose(beta(returns, returns), 1.0)

    def test_beta_nan_for_zero_variance_benchmark(self):
        a = pd.Series([0.01, 0.02, 0.01])
        b = pd.Series([0.0, 0.0, 0.0])
        assert np.isnan(beta(a, b))

    def test_rolling_correlation_perfect_for_identical_series(self):
        rng = np.random.default_rng(0)
        a = pd.Series(rng.normal(0, 0.01, 50))
        result = rolling_correlation(a, a, window=10)
        assert np.isclose(result.iloc[-1], 1.0)

    def test_rolling_correlation_skips_days_either_series_is_missing(self):
        # equities have no weekend rows in a frame that also holds daily crypto
        rng = np.random.default_rng(1)
        dates = pd.date_range("2024-01-01", periods=120, freq="D")
        a = pd.Series(rng.normal(0, 0.01, 120), index=dates)
        weekday = dates.dayofweek < 5
        a[~weekday] = np.nan
        result = rolling_correlation(a, a * 2, window=30)
        assert result.notna().sum() == weekday.sum() - 29
        assert np.allclose(result.dropna(), 1.0)

    def test_index_summary_keys(self):
        returns = pd.Series([0.01, -0.02, 0.03])
        summary = index_summary(returns)
        for key in ["annualized_volatility", "cumulative_return", "max_drawdown", "sharpe_ratio"]:
            assert key in summary
