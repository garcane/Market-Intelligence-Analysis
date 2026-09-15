import numpy as np
import pandas as pd

from src.analytics.event_study import (
    abnormal_return_window,
    average_car_across_events,
    cumulative_abnormal_return,
    event_window_returns,
)


def _series(n=30, start="2024-01-01"):
    dates = pd.date_range(start, periods=n, freq="D")
    return dates


class TestEventWindowReturns:
    def test_extracts_correct_window_around_event(self):
        dates = _series(30)
        returns = pd.Series(np.arange(30, dtype=float))  # returns[i] = i, easy to verify
        event_date = str(dates[15].date())
        window = event_window_returns(returns, pd.Series(dates), event_date, window=5)
        assert window is not None
        assert window.index.tolist() == list(range(-5, 6))
        assert window.loc[0] == 15.0  # T0 return
        assert window.loc[-5] == 10.0
        assert window.loc[5] == 20.0

    def test_returns_none_when_window_extends_before_data_start(self):
        dates = _series(30)
        returns = pd.Series(np.arange(30, dtype=float))
        event_date = str(dates[2].date())  # too close to the start for a 5-day lookback
        window = event_window_returns(returns, pd.Series(dates), event_date, window=5)
        assert window is None

    def test_returns_none_when_window_extends_past_data_end(self):
        dates = _series(30)
        returns = pd.Series(np.arange(30, dtype=float))
        event_date = str(dates[28].date())
        window = event_window_returns(returns, pd.Series(dates), event_date, window=5)
        assert window is None

    def test_uses_nearest_trading_day_on_or_after_a_weekend_event_date(self):
        # simulate an equity calendar with a gap (event date itself missing, e.g. a weekend)
        dates = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-05", "2024-01-08",
                                 "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12",
                                 "2024-01-15", "2024-01-16", "2024-01-17", "2024-01-18"])
        returns = pd.Series(range(len(dates)), dtype=float)
        # event date 2024-01-06 (a Saturday, not in the series) -> should snap to 2024-01-08
        window = event_window_returns(returns, pd.Series(dates), "2024-01-06", window=2)
        assert window is not None
        assert window.loc[0] == 3.0  # index of 2024-01-08


class TestAbnormalReturns:
    def test_abnormal_return_is_asset_minus_benchmark(self):
        dates = pd.Series(_series(30))
        asset_returns = pd.Series(np.full(30, 0.05))
        bench_returns = pd.Series(np.full(30, 0.02))
        event_date = str(dates.iloc[15].date())
        ar = abnormal_return_window(asset_returns, dates, bench_returns, dates, event_date, window=3)
        assert np.allclose(ar.values, 0.03)

    def test_cumulative_abnormal_return_accumulates(self):
        ar = pd.Series([0.01, -0.02, 0.03], index=[-1, 0, 1])
        car = cumulative_abnormal_return(ar)
        assert np.isclose(car.loc[1], 0.01 - 0.02 + 0.03)


class TestAverageCAR:
    def test_aar_is_mean_across_events(self):
        windows = {
            "event_a": pd.Series([0.02, 0.01, -0.01], index=[-1, 0, 1]),
            "event_b": pd.Series([0.04, 0.03, 0.01], index=[-1, 0, 1]),
        }
        result = average_car_across_events(windows)
        assert np.isclose(result.loc[0, "AAR"], (0.01 + 0.03) / 2)
        assert result.loc[0, "n_events"] == 2

    def test_caar_at_final_day_equals_sum_of_aar(self):
        windows = {
            "event_a": pd.Series([0.01, 0.02], index=[0, 1]),
            "event_b": pd.Series([0.03, -0.01], index=[0, 1]),
        }
        result = average_car_across_events(windows)
        assert np.isclose(result.loc[1, "CAAR"], result["AAR"].sum())
