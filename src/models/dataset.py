"""Builds the model-ready X/y matrices from data/processed/ml_dataset/ml_dataset.parquet.

Feature selection is an explicit whitelist, not "everything except a
blacklist" — the merged ingestion-architecture reconciliation left several
provider-metadata columns (asset_id, currency, source, source_record_id,
ingested_at) riding along in the feature table, and a blacklist approach would
silently let a future added column leak into the model. A whitelist fails
loudly (KeyError) instead when the feature table's shape changes unexpectedly.

Raw price/volume levels (open, high, low, close, adj_close, volume,
market_cap, sma_*) are deliberately excluded — they're non-stationary and not
comparable in scale across assets (BTC's close is ~1000x MSFT's); only
returns/ratios/indicators derived from them are used as features.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

MARKET_FEATURES = [
    "return_1d", "log_return_1d", "rolling_vol_7d", "rolling_vol_30d", "drawdown",
    "lag_return_1d", "lag_return_3d", "lag_return_5d", "lag_return_10d",
    "rolling_return_5d", "rolling_return_10d", "rolling_return_30d",
    "momentum_10d", "momentum_30d", "rsi_14d",
    "volume_change_1d", "volume_ratio_10d",
]
CROSS_SECTIONAL_FEATURES = ["market_return", "ai_index_return", "relative_performance"]
# These have structural NaN — sparse news coverage (sentiment_*) or an asset
# with no defined AI-category peer group (sector_return, crypto assets) —
# and get a missingness flag + constant-0 imputation rather than row-dropping.
SPARSE_FEATURES = [
    "sentiment_current", "lag_sentiment_1d", "lag_sentiment_3d", "lag_sentiment_5d",
    "rolling_mean_sentiment_7d", "sentiment_volatility", "positive_ratio", "negative_ratio",
    "news_volume", "sector_return", "relative_sector_performance",
]
CATEGORICAL_FEATURES = ["market_id"]

ALL_FEATURES = MARKET_FEATURES + CROSS_SECTIONAL_FEATURES + SPARSE_FEATURES + CATEGORICAL_FEATURES


def impute_sparse_features(df: pd.DataFrame, sparse_cols: list[str] = SPARSE_FEATURES) -> pd.DataFrame:
    """Adds a `{col}_missing` flag before filling NaN with 0, so a model can
    tell "genuinely zero" apart from "no data" if the signal is useful.
    `news_volume`'s NaN (if any) means "no article that day", which already
    equals 0 in the source data — flagged the same way for consistency.

    A sparse column can be entirely absent from `df`, not just NaN within
    it — e.g. if every asset in a given batch lacks an AI-category sector
    match, src/features/pipeline.py's per-asset frames never contribute a
    `sector_return` column at all, so it's missing after concatenation
    rather than present-with-NaN (caught by tests/test_pipeline.py's
    end-to-end integration test, using synthetic assets with no real-world
    entity/sector match — a case that never occurred with the actual
    ingested universe, where at least one asset always has a sector match,
    but is still a real robustness gap for any future batch that doesn't).
    Columns absent entirely are created as all-NaN before the same
    missingness-flag + fillna(0) logic runs, so this function's behavior
    doesn't depend on what the upstream feature pipeline happened to include.
    """
    df = df.copy()
    for col in sparse_cols:
        if col not in df.columns:
            df[col] = float("nan")
        df[f"{col}_missing"] = df[col].isna().astype(int)
        df[col] = df[col].fillna(0.0)
    return df


def build_dataset_for_horizon(ml_dataset: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Filters to rows usable for this horizon (drops excluded_embargo /
    excluded_no_target), drops warm-up rows with NaN in market/cross-sectional
    features (unavoidable early-history rows, not sparse data), and imputes
    the genuinely sparse feature group. Returns one dataframe with `split`
    and `y` columns added, ready to be sliced by split.
    """
    split_col = f"split_{horizon}d"
    target_col = f"target_{horizon}d"
    df = ml_dataset[ml_dataset[split_col].isin(["train", "validation", "test"])].copy()

    dense_cols = MARKET_FEATURES + CROSS_SECTIONAL_FEATURES
    before = len(df)
    df = df.dropna(subset=dense_cols)
    dropped = before - len(df)

    df = impute_sparse_features(df)
    df["split"] = df[split_col]
    df["y"] = df[target_col]
    return df, dropped


def get_feature_columns() -> tuple[list[str], list[str]]:
    numeric = MARKET_FEATURES + CROSS_SECTIONAL_FEATURES + SPARSE_FEATURES + \
        [f"{c}_missing" for c in SPARSE_FEATURES]
    categorical = CATEGORICAL_FEATURES
    return numeric, categorical


def build_preprocessor() -> ColumnTransformer:
    numeric, categorical = get_feature_columns()
    return ColumnTransformer([
        ("numeric", StandardScaler(), numeric),
        ("categorical", OneHotEncoder(handle_unknown="ignore"), categorical),
    ])


def split_xy(df: pd.DataFrame, split_name: str) -> tuple[pd.DataFrame, np.ndarray]:
    numeric, categorical = get_feature_columns()
    subset = df[df["split"] == split_name]
    X = subset[numeric + categorical]
    y = subset["y"].astype(int).values
    return X, y
