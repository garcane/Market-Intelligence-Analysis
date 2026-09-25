"""Orchestrates robustness testing (target spec §19). Run as:
python -m src.models.run_robustness
"""
from __future__ import annotations

import json
import logging

import joblib
import pandas as pd

from src.config import OUTPUTS_DIR, PROCESSED_DIR
from src.features.target import PRIMARY_HORIZON
from src.models.dataset import build_dataset_for_horizon, split_xy
from src.models.robustness import (
    evaluate_across_horizons,
    evaluate_across_seeds,
    evaluate_across_thresholds,
    evaluate_by_asset_group,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL_DIR = OUTPUTS_DIR / "model_results" / "models"
PRIMARY_MODEL = "xgboost"  # Stage 9's leaderboard winner


def main() -> None:
    ml_dataset = pd.read_parquet(PROCESSED_DIR / "ml_dataset" / "ml_dataset.parquet")
    features = pd.read_parquet(PROCESSED_DIR / "features" / "features.parquet")

    report = {"primary_model": PRIMARY_MODEL}

    logger.info("=== Robustness: across horizons ===")
    report["by_horizon"] = evaluate_across_horizons(ml_dataset, PRIMARY_MODEL)
    for h, m in report["by_horizon"].items():
        logger.info("horizon=%s: PR-AUC=%.3f ROC-AUC=%.3f n_val=%d", h, m["pr_auc"], m["roc_auc"], m["n_val"])

    logger.info("=== Robustness: across thresholds ===")
    market_dir = PROCESSED_DIR.parent / "raw" / "market_prices"
    from src.features.target import MODELING_MARKET_IDS
    market_prices = {mid: pd.read_parquet(market_dir / f"{mid}.parquet") for mid in MODELING_MARKET_IDS}
    report["by_threshold"] = evaluate_across_thresholds(market_prices, features, model_name=PRIMARY_MODEL)
    for t, m in report["by_threshold"].items():
        logger.info("threshold=%s: PR-AUC=%.3f positive_rate=%.3f", t, m["pr_auc"], m["positive_rate"])

    logger.info("=== Robustness: across random seeds ===")
    report["by_seed"] = evaluate_across_seeds(ml_dataset, PRIMARY_MODEL, horizon=PRIMARY_HORIZON)
    logger.info("PR-AUC across seeds: mean=%.3f std=%.4f (values=%s)",
                report["by_seed"]["mean_pr_auc"], report["by_seed"]["std_pr_auc"], report["by_seed"]["pr_auc_by_seed"])

    logger.info("=== Robustness: by asset group (equity vs crypto) ===")
    prepared, _ = build_dataset_for_horizon(ml_dataset, horizon=PRIMARY_HORIZON)
    X_val, y_val = split_xy(prepared, "validation")
    model = joblib.load(MODEL_DIR / f"{PRIMARY_MODEL}_h{PRIMARY_HORIZON}d.joblib")
    report["by_asset_group"] = evaluate_by_asset_group(model, X_val, y_val)
    for group, m in report["by_asset_group"].items():
        logger.info("group=%s: n=%d PR-AUC=%.3f ROC-AUC=%.3f", group, m["n"], m["pr_auc"], m["roc_auc"])

    with open(PROCESSED_DIR / "robustness_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Robustness report written to %s", PROCESSED_DIR / "robustness_report.json")


if __name__ == "__main__":
    main()
