"""Stage 11: event study methodology. Abnormal return = asset return - benchmark
return on the same trading day (a simple relative-return "market-model-lite"
approach, not a full CAPM regression with estimated beta over a clean
pre-event estimation window — documented as a methodological simplification
in EVENT_STUDY.md, not hidden).

Event windows are built on TRADING-DAY row position within each asset's own
series (nearest available date >= the nominal event date is T0), not calendar-
day arithmetic — avoids the weekend-gap problem for equities that a naive
`event_date - 5 days` would hit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _t0_index(dates: pd.Series, event_date: str) -> int | None:
    dates = pd.to_datetime(dates).reset_index(drop=True)
    event_ts = pd.Timestamp(event_date)
    candidates = dates[dates >= event_ts]
    if candidates.empty:
        return None
    return candidates.index[0]


def event_window_returns(returns: pd.Series, dates: pd.Series, event_date: str,
                          window: int = 5) -> pd.Series | None:
    """Returns a Series indexed by relative trading day (-window..+window)
    around the event. None if the event date or its window falls outside
    the available data.
    """
    t0 = _t0_index(dates, event_date)
    if t0 is None or t0 - window < 0 or t0 + window >= len(returns):
        return None
    values = returns.reset_index(drop=True).iloc[t0 - window: t0 + window + 1]
    return pd.Series(values.values, index=range(-window, window + 1))


def abnormal_return_window(asset_returns: pd.Series, asset_dates: pd.Series,
                            benchmark_returns: pd.Series, benchmark_dates: pd.Series,
                            event_date: str, window: int = 5) -> pd.Series | None:
    asset_window = event_window_returns(asset_returns, asset_dates, event_date, window)
    bench_window = event_window_returns(benchmark_returns, benchmark_dates, event_date, window)
    if asset_window is None or bench_window is None:
        return None
    return asset_window - bench_window


def cumulative_abnormal_return(abnormal_returns: pd.Series) -> pd.Series:
    return abnormal_returns.cumsum()


def average_car_across_events(event_windows: dict[str, pd.Series]) -> pd.DataFrame:
    """event_windows: {event_id: abnormal_return_window Series}. Returns a
    DataFrame of AAR (average abnormal return) and CAAR (cumulative average
    abnormal return) across all provided events, per relative trading day —
    the classic event-study aggregation, so individual noisy single-event
    reactions don't get over-interpreted.
    """
    combined = pd.DataFrame(event_windows)
    aar = combined.mean(axis=1)
    caar = aar.cumsum()
    return pd.DataFrame({"AAR": aar, "CAAR": caar, "n_events": combined.notna().sum(axis=1)})
