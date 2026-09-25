"""Ablation study (target spec §20, unlabeled but explicitly requested):
does adding sentiment/cross-sectional features actually improve predictive
performance over market features alone? Four experiments, each training the
same architecture (XGBoost, Stage 9's leaderboard winner) on a different
feature subset.

Experiment D is "Market + Sentiment + Cross-sectional", not the spec's
literal "Market + Sentiment + AI event features" — AI event features were
never built (see FEATURES.md's Stage 6 deferral: no event data source
exists). Substituting the cross-sectional features (market/sector/AI-index
return, all real and already built) rather than skipping Experiment D
entirely keeps the ablation's actual point intact: does adding the "extra"
feature groups beyond raw market data help.
"""
from __future__ import annotations

import pandas as pd

from src.models.classifiers import build_models
from src.models.dataset import (
    CROSS_SECTIONAL_FEATURES,
    MARKET_FEATURES,
    SPARSE_FEATURES,
    build_dataset_for_horizon,
)
from src.models.evaluate import compute_metrics

SENTIMENT_FEATURES = [c for c in SPARSE_FEATURES if c not in ("sector_return", "relative_sector_performance")]
SECTOR_FEATURES = ["sector_return", "relative_sector_performance"]

EXPERIMENTS = {
    "A_market_only": MARKET_FEATURES,
    "B_sentiment_only": SENTIMENT_FEATURES,
    "C_market_plus_sentiment": MARKET_FEATURES + SENTIMENT_FEATURES,
    "D_market_plus_sentiment_plus_crosssectional":
        MARKET_FEATURES + SENTIMENT_FEATURES + CROSS_SECTIONAL_FEATURES + SECTOR_FEATURES,
}


def _feature_cols_with_missing_flags(cols: list[str]) -> list[str]:
    result = list(cols)
    for c in cols:
        if c in SPARSE_FEATURES:
            result.append(f"{c}_missing")
    return result


def run_ablation(ml_dataset: pd.DataFrame, horizon: int = 5, model_name: str = "xgboost") -> dict:
    prepared, _ = build_dataset_for_horizon(ml_dataset, horizon=horizon)
    train = prepared[prepared["split"] == "train"]
    val = prepared[prepared["split"] == "validation"]

    results = {}
    for exp_name, base_cols in EXPERIMENTS.items():
        cols = _feature_cols_with_missing_flags(base_cols) + ["market_id"]
        X_train, y_train = train[cols], train["y"].astype(int).values
        X_val, y_val = val[cols], val["y"].astype(int).values

        model = build_models()[model_name]
        # rebuild the preprocessor to match this experiment's actual column set
        from sklearn.compose import ColumnTransformer
        from sklearn.preprocessing import OneHotEncoder, StandardScaler
        numeric_cols = [c for c in cols if c != "market_id"]
        model.set_params(preprocessor=ColumnTransformer([
            ("numeric", StandardScaler(), numeric_cols),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), ["market_id"]),
        ]))

        model.fit(X_train, y_train)
        proba = model.predict_proba(X_val)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics = compute_metrics(y_val, pred, proba)
        results[exp_name] = {"n_features": len(base_cols), "n_train": len(y_train), **metrics}
    return results
