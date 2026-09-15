import numpy as np
import pandas as pd

from src.features.target import add_classification_targets, add_future_returns, build_target_table
from src.features.target_analysis import class_balance_grid, realized_volatility_by_asset


def _price_df(n=40, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = 100 * np.cumprod(1 + rng.normal(0.0, 0.02, n))
    return pd.DataFrame({"date": dates, "close": close})


class TestFutureReturns:
    def test_future_return_matches_manual_calculation(self):
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=5),
                            "close": [100.0, 102.0, 105.0, 103.0, 110.0]})
        result = add_future_returns(df, horizons=(2,))
        # future_return_2d at row 0 = close[2]/close[0] - 1 = 105/100 - 1
        assert np.isclose(result["future_return_2d"].iloc[0], 0.05)

    def test_last_h_rows_are_nan(self):
        df = _price_df(n=20)
        result = add_future_returns(df, horizons=(5,))
        assert result["future_return_5d"].iloc[-5:].isna().all()
        assert result["future_return_5d"].iloc[:-5].notna().all()

    def test_is_genuinely_forward_looking_not_accidentally_backward(self):
        # A monotonically increasing price series must show positive future
        # returns everywhere they're defined — this would fail if shift(-h)
        # were accidentally shift(h) (i.e. looking backward instead of forward).
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=10),
                            "close": np.linspace(100, 200, 10)})
        result = add_future_returns(df, horizons=(3,))
        valid = result["future_return_3d"].dropna()
        assert (valid > 0).all()


class TestClassificationTarget:
    def test_target_is_binary_where_defined(self):
        df = _price_df()
        df = add_future_returns(df, horizons=(5,))
        df = add_classification_targets(df, horizons=(5,), threshold=0.02)
        non_null = df["target_5d"].dropna()
        assert set(non_null.unique()).issubset({0.0, 1.0})

    def test_target_nan_exactly_where_future_return_nan(self):
        df = _price_df()
        df = add_future_returns(df, horizons=(5,))
        df = add_classification_targets(df, horizons=(5,), threshold=0.02)
        assert (df["target_5d"].isna() == df["future_return_5d"].isna()).all()

    def test_threshold_logic_is_strictly_greater_than(self):
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3),
                            "future_return_5d": [0.02, 0.021, 0.019]})
        result = add_classification_targets(df, horizons=(5,), threshold=0.02)
        assert result["target_5d"].iloc[0] == 0.0  # exactly at threshold -> not positive
        assert result["target_5d"].iloc[1] == 1.0
        assert result["target_5d"].iloc[2] == 0.0

    def test_per_horizon_thresholds(self):
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=3),
                            "future_return_1d": [0.005, 0.015, 0.0],
                            "future_return_5d": [0.03, 0.01, 0.0]})
        result = add_classification_targets(df, horizons=(1, 5), threshold={1: 0.01, 5: 0.02})
        assert result["target_1d"].tolist() == [0.0, 1.0, 0.0]
        assert result["target_5d"].tolist() == [1.0, 0.0, 0.0]

    def test_horizons_are_not_mixed_in_one_column(self):
        df = _price_df()
        df = add_future_returns(df, horizons=(1, 5, 10))
        df = add_classification_targets(df, horizons=(1, 5, 10), threshold=0.02)
        # each horizon gets its own independent target column
        assert {"target_1d", "target_5d", "target_10d"}.issubset(df.columns)
        assert not df["target_1d"].equals(df["target_5d"])


class TestBuildTargetTable:
    def test_combines_multiple_assets(self):
        prices = {"A": _price_df(seed=1), "B": _price_df(seed=2)}
        result = build_target_table(prices, horizons=(5,), threshold=0.02)
        assert set(result["market_id"].unique()) == {"A", "B"}
        assert not result.duplicated(subset=["market_id", "date"]).any()


class TestTargetAnalysis:
    def test_class_balance_grid_positive_rate_bounded(self):
        prices = {"A": _price_df(seed=1)}
        grid = class_balance_grid(prices, horizons=(5,), thresholds=(0.0, 0.02))
        assert (grid["positive_rate"].dropna() >= 0).all()
        assert (grid["positive_rate"].dropna() <= 1).all()

    def test_higher_threshold_never_increases_positive_rate(self):
        prices = {"A": _price_df(seed=1)}
        grid = class_balance_grid(prices, horizons=(5,), thresholds=(0.0, 0.02, 0.05))
        rates = grid.sort_values("threshold")["positive_rate"].tolist()
        assert rates == sorted(rates, reverse=True)

    def test_realized_volatility_positive(self):
        prices = {"A": _price_df(seed=1)}
        vol = realized_volatility_by_asset(prices)
        assert (vol["daily_vol"] > 0).all()
        assert np.isclose(vol["vol_5d"].iloc[0], vol["daily_vol"].iloc[0] * np.sqrt(5))
