"""Scores the latest feature row per modelling asset with each saved model.

These rows are the newest in the data, so they have no realised target yet:
this produces forward-looking probabilities only and computes no metrics, which
keeps the held-out test set unscored. Used by the web app's predictions page.
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd

from src.config import OUTPUTS_DIR, PROCESSED_DIR
from src.features.target import DEFAULT_THRESHOLD, MODELING_MARKET_IDS, PRIMARY_HORIZON
from src.models.dataset import CROSS_SECTIONAL_FEATURES, MARKET_FEATURES, get_feature_columns, impute_sparse_features

MODEL_DIR = OUTPUTS_DIR / "model_results" / "models"
FEATURES_PATH = PROCESSED_DIR / "features" / "features.parquet"


def latest_feature_rows(features: pd.DataFrame, market_ids=MODELING_MARKET_IDS) -> pd.DataFrame:
    """The most recent row per asset that has every dense feature, prepared the
    same way as training rows (build_dataset_for_horizon)."""
    df = features[features["market_id"].isin(market_ids)]
    df = df.dropna(subset=MARKET_FEATURES + CROSS_SECTIONAL_FEATURES)
    latest = df.sort_values("date").groupby("market_id", as_index=False).tail(1)
    return impute_sparse_features(latest).sort_values("market_id").reset_index(drop=True)


def predict_latest(horizon: int = PRIMARY_HORIZON, features: pd.DataFrame | None = None,
                   model_dir: Path = MODEL_DIR, report_path: Path | None = None) -> dict:
    if features is None:
        features = pd.read_parquet(FEATURES_PATH)
    rows = latest_feature_rows(features)
    numeric, categorical = get_feature_columns()
    X = rows[numeric + categorical]

    report_path = report_path or PROCESSED_DIR / f"model_report_h{horizon}d.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    val_metrics = {name: m.get("validation_metrics", {}) for name, m in report.get("models", {}).items()}

    models = {}
    for path in sorted(model_dir.glob(f"*_h{horizon}d.joblib")):
        name = path.name[: -len(f"_h{horizon}d.joblib")]
        proba = joblib.load(path).predict_proba(X)[:, 1]
        models[name] = {
            "validation_pr_auc": val_metrics.get(name, {}).get("pr_auc"),
            "validation_roc_auc": val_metrics.get(name, {}).get("roc_auc"),
            "probabilities": dict(zip(rows["market_id"], map(float, proba))),
        }

    return {
        "horizon": horizon,
        "target": f"{horizon}-day forward return above {DEFAULT_THRESHOLD:.0%}",
        "validation_positive_rate": report.get("val_positive_rate"),
        "leaderboard": report.get("leaderboard", []),
        "assets": [{"market_id": r.market_id, "as_of": str(pd.Timestamp(r.date).date()),
                    "close": float(r.close)} for r in rows.itertuples()],
        "models": models,
    }
