"""Robustness testing (target spec §19, unlabeled but mandatory): do the
Stage 9 conclusions survive different horizons, thresholds, random seeds,
and asset subgroups? Every function here reports results as-is, including
negative ones — the spec is explicit that a model winning overall but
performing poorly on a subgroup must be reported, not hidden.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.models.classifiers import build_models
from src.models.dataset import build_dataset_for_horizon, split_xy
from src.models.evaluate import compute_metrics

EQUITY_ASSETS = {"NVDA", "MSFT", "TSM"}
CRYPTO_ASSETS = {"BTC", "ETH", "SOL"}


def evaluate_across_horizons(ml_dataset: pd.DataFrame, model_name: str = "xgboost",
                              horizons: tuple[int, ...] = (1, 5, 10)) -> dict:
    """Same model architecture, same ml_dataset, different target horizon —
    does the leaderboard-winning architecture hold up at 1-day and 10-day
    horizons, or was 5-day cherry-picked good luck?
    """
    results = {}
    for h in horizons:
        prepared, _ = build_dataset_for_horizon(ml_dataset, horizon=h)
        X_train, y_train = split_xy(prepared, "train")
        X_val, y_val = split_xy(prepared, "validation")
        model = build_models()[model_name]
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_val)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics = compute_metrics(y_val, pred, proba)
        results[f"{h}d"] = {"n_train": len(y_train), "n_val": len(y_val), **metrics}
    return results


def evaluate_across_thresholds(market_prices: dict[str, pd.DataFrame], features: pd.DataFrame,
                                thresholds: tuple[float, ...] = (0.01, 0.02, 0.03),
                                horizon: int = 5, model_name: str = "xgboost") -> dict:
    """Same model, same horizon, different classification threshold — rebuilds
    the target table at each threshold (features are threshold-independent,
    only target/split need rebuilding) and retrains.
    """
    from src.models.split import add_split_labels
    from src.features.target import build_target_table

    results = {}
    for t in thresholds:
        targets = build_target_table(market_prices, horizons=(horizon,), threshold=t)
        merged = features.merge(targets, on=["market_id", "date"], how="inner")
        merged = add_split_labels(merged, horizons=(horizon,))
        prepared, _ = build_dataset_for_horizon(merged, horizon=horizon)
        X_train, y_train = split_xy(prepared, "train")
        X_val, y_val = split_xy(prepared, "validation")
        model = build_models()[model_name]
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_val)[:, 1]
        pred = (proba >= 0.5).astype(int)
        metrics = compute_metrics(y_val, pred, proba)
        results[str(t)] = {"n_train": len(y_train), "n_val": len(y_val), **metrics}
    return results


def evaluate_across_seeds(ml_dataset: pd.DataFrame, model_name: str = "xgboost",
                           horizon: int = 5, seeds: tuple[int, ...] = (1, 2, 3, 4, 5)) -> dict:
    """Same everything except the model's random_state — how much does
    validation PR-AUC vary just from training-randomness, independent of any
    real design choice? A model whose seed-to-seed variance rivals the gap
    between models in the Stage 9 leaderboard would make that leaderboard's
    ordering suspect.
    """
    from sklearn.base import clone

    prepared, _ = build_dataset_for_horizon(ml_dataset, horizon=horizon)
    X_train, y_train = split_xy(prepared, "train")
    X_val, y_val = split_xy(prepared, "validation")

    pr_aucs = []
    for seed in seeds:
        model = clone(build_models()[model_name])
        model.set_params(model__random_state=seed)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_val)[:, 1]
        pr_aucs.append(compute_metrics(y_val, (proba >= 0.5).astype(int), proba)["pr_auc"])

    return {"seeds": list(seeds), "pr_auc_by_seed": pr_aucs,
            "mean_pr_auc": float(np.mean(pr_aucs)), "std_pr_auc": float(np.std(pr_aucs))}


def evaluate_by_asset_group(model, X_val: pd.DataFrame, y_val: np.ndarray) -> dict:
    """Splits validation performance by equity vs crypto — the one subgroup
    split the current 6-asset universe actually supports meaningfully.
    `X_val` is the raw (pre-preprocessing) feature frame from split_xy, which
    still has a plain `market_id` string column — one-hot encoding happens
    inside the model Pipeline's own ColumnTransformer at predict() time, not
    before, so group membership is read directly from that column here.
    """
    proba = model.predict_proba(X_val)[:, 1]
    pred = (proba >= 0.5).astype(int)

    results = {}
    for group_name, group_assets in [("equity", EQUITY_ASSETS), ("crypto", CRYPTO_ASSETS)]:
        mask = X_val["market_id"].isin(group_assets).values
        if mask.sum() == 0:
            continue
        metrics = compute_metrics(y_val[mask], pred[mask], proba[mask])
        results[group_name] = {"n": int(mask.sum()), **metrics}
    return results
