import numpy as np
import pandas as pd

from src.features.target import add_classification_targets, add_future_returns
from src.models.split import add_split_labels, assign_split, walk_forward_folds


def _asset_df(n=60, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, n))
    return pd.DataFrame({"date": dates, "close": close})


class TestAssignSplit:
    def test_basic_partition_train_val_test(self):
        df = _asset_df(n=60)
        df = add_future_returns(df, horizons=(5,))
        # train_end day 30, val_end day 45 (0-indexed from 2024-01-01)
        train_end = df["date"].iloc[29]
        val_end = df["date"].iloc[44]
        split = assign_split(df, horizon=5, train_end=str(train_end.date()), val_end=str(val_end.date()))
        assert set(split.unique()).issubset({"train", "validation", "test", "excluded_embargo", "excluded_no_target"})
        assert (split == "train").any()
        assert (split == "validation").any()
        assert (split == "test").any()

    def test_no_row_appears_in_two_splits(self):
        # trivially true by construction (one Series value per row) but assert
        # the meaningful corollary: assigned splits are chronologically ordered.
        df = _asset_df(n=60)
        df = add_future_returns(df, horizons=(5,))
        train_end = df["date"].iloc[29]
        val_end = df["date"].iloc[44]
        split = assign_split(df, horizon=5, train_end=str(train_end.date()), val_end=str(val_end.date()))
        df["split"] = split
        train_max = df.loc[df["split"] == "train", "date"].max()
        val_min = df.loc[df["split"] == "validation", "date"].min()
        val_max = df.loc[df["split"] == "validation", "date"].max()
        test_min = df.loc[df["split"] == "test", "date"].min()
        assert train_max < val_min
        assert val_max < test_min

    def test_embargo_excludes_rows_whose_target_crosses_boundary(self):
        # Row at train_end has a target that resolves 5 days later, past
        # train_end — it must be embargoed, not counted as "train".
        df = _asset_df(n=60)
        df = add_future_returns(df, horizons=(5,))
        train_end = df["date"].iloc[29]  # index 29
        val_end = df["date"].iloc[44]
        split = assign_split(df, horizon=5, train_end=str(train_end.date()), val_end=str(val_end.date()))
        # rows at indices 25..29 (dates within 5 days before train_end) have
        # target_date_5d > train_end and must be embargoed, not "train"
        for i in range(25, 30):
            assert split.iloc[i] == "excluded_embargo", f"row {i} should be embargoed but got {split.iloc[i]!r}"
        # a row safely before the embargo zone should be "train"
        assert split.iloc[20] == "train"

    def test_no_embargo_needed_check_train_target_dates_never_exceed_train_end(self):
        # The actual leakage guarantee: every row labeled "train" has its
        # target resolving ON OR BEFORE train_end — i.e. no train label
        # encodes information from the validation period.
        df = _asset_df(n=60)
        df = add_future_returns(df, horizons=(5,))
        train_end = pd.Timestamp(df["date"].iloc[29])
        val_end = df["date"].iloc[44]
        split = assign_split(df, horizon=5, train_end=str(train_end.date()), val_end=str(val_end.date()))
        train_rows = df[split == "train"]
        assert (train_rows["target_date_5d"] <= train_end).all()

    def test_higher_horizon_embargoes_more_rows(self):
        df = _asset_df(n=60)
        df = add_future_returns(df, horizons=(1, 10))
        train_end = df["date"].iloc[29]
        val_end = df["date"].iloc[44]
        split_1 = assign_split(df, horizon=1, train_end=str(train_end.date()), val_end=str(val_end.date()))
        split_10 = assign_split(df, horizon=10, train_end=str(train_end.date()), val_end=str(val_end.date()))
        assert (split_10 == "excluded_embargo").sum() > (split_1 == "excluded_embargo").sum()

    def test_test_rows_with_no_future_price_are_excluded_not_test(self):
        df = _asset_df(n=60)
        df = add_future_returns(df, horizons=(5,))
        train_end = df["date"].iloc[29]
        val_end = df["date"].iloc[44]
        split = assign_split(df, horizon=5, train_end=str(train_end.date()), val_end=str(val_end.date()))
        # the last 5 rows have no target_date_5d (NaN) -> must not be "test"
        assert (split.iloc[-5:] != "test").all()
        assert (split.iloc[-5:] == "excluded_no_target").all()


class TestAddSplitLabels:
    def test_multiple_assets_and_horizons(self):
        df1 = _asset_df(n=60, seed=1)
        df1["market_id"] = "A"
        df2 = _asset_df(n=60, seed=2)
        df2["market_id"] = "B"
        combined = pd.concat([df1, df2], ignore_index=True)
        combined = add_future_returns(combined.drop(columns=["market_id"]).assign(market_id=combined["market_id"]),
                                       horizons=(1, 5))
        # add_future_returns sorts by date globally; redo per-asset to be safe
        frames = []
        for mid, g in combined.groupby("market_id"):
            frames.append(add_future_returns(g.drop(columns=["market_id"]), horizons=(1, 5)).assign(market_id=mid))
        combined = pd.concat(frames, ignore_index=True)

        train_end = df1["date"].iloc[29]
        val_end = df1["date"].iloc[44]
        result = add_split_labels(combined, horizons=(1, 5), train_end=str(train_end.date()), val_end=str(val_end.date()))
        assert "split_1d" in result.columns and "split_5d" in result.columns
        for mid in ["A", "B"]:
            sub = result[result["market_id"] == mid]
            assert (sub["split_1d"] == "train").any()
            assert (sub["split_5d"] == "train").any()

    def test_never_shuffles_rows(self):
        # regression guard against reintroducing a random split anywhere in
        # this module — row order in, row order out.
        df = _asset_df(n=30)
        df = add_future_returns(df, horizons=(5,))
        df["market_id"] = "A"
        result = add_split_labels(df, horizons=(5,), train_end="2024-01-15", val_end="2024-01-22")
        assert result["date"].tolist() == sorted(result["date"].tolist())


class TestWalkForwardFolds:
    def test_folds_are_non_overlapping_and_expanding(self):
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        folds = walk_forward_folds(dates, n_folds=3, min_train_days=40, test_days=20)
        assert len(folds) >= 1
        for train_end, test_start, test_end in folds:
            assert train_end < test_start <= test_end
        # expanding: each fold's train_end should be later than the previous
        train_ends = [f[0] for f in folds]
        assert train_ends == sorted(train_ends)
