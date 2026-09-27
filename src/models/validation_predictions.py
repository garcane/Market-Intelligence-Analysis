"""Validation-split predictions for the web app's interactive model charts.

Exports each validation row's true label and every model's predicted
probability, so the browser can draw ROC and precision-recall curves and
recompute confusion matrices at any threshold. At a threshold of 0.5 the
counts reproduce model_report_h{h}d.json exactly (predicted positive means
probability >= 0.5, as in train_baselines).

The naive baselines are exported as fixed confusion counts rather than
probabilities: the random baseline draws its 0/1 predictions independently of
its scores (src/models/baselines.py), so no threshold regenerates them.

train_baselines writes this file after every training run. Run this module to
rebuild it from the saved models without retraining:
    python -m src.models.validation_predictions
"""
from __future__ import annotations

import json
import logging

import joblib
import numpy as np
import pandas as pd

from src.config import OUTPUTS_DIR, PROCESSED_DIR
from src.features.target import PRIMARY_HORIZON
from src.models.dataset import build_dataset_for_horizon, split_xy

logger = logging.getLogger(__name__)

MODEL_DIR = OUTPUTS_DIR / "model_results" / "models"
PROBA_DECIMALS = 6


def output_path(horizon: int):
    return PROCESSED_DIR / f"validation_predictions_h{horizon}d.json"


def build_payload(horizon: int, y_val: np.ndarray, probas: dict[str, np.ndarray],
                  baselines: dict[str, dict[str, int]]) -> dict:
    y_val = np.asarray(y_val).astype(int)
    for name, proba in probas.items():
        if len(proba) != len(y_val):
            raise ValueError(f"{name}: {len(proba)} probabilities for {len(y_val)} validation rows")
    return {
        "horizon": horizon,
        "n_validation": int(len(y_val)),
        "base_rate": float(y_val.mean()) if len(y_val) else None,
        "y_true": y_val.tolist(),
        "models": {name: np.round(np.asarray(p, dtype=float), PROBA_DECIMALS).tolist() for name, p in probas.items()},
        "baselines": baselines,
    }


def write(payload: dict) -> None:
    with open(output_path(payload["horizon"]), "w", encoding="utf-8") as f:
        json.dump(payload, f, separators=(",", ":"))


def main(horizon: int = PRIMARY_HORIZON) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    with open(PROCESSED_DIR / f"model_report_h{horizon}d.json", encoding="utf-8") as f:
        report = json.load(f)
    ml_dataset = pd.read_parquet(PROCESSED_DIR / "ml_dataset" / "ml_dataset.parquet")
    prepared, _ = build_dataset_for_horizon(ml_dataset, horizon)
    X_val, y_val = split_xy(prepared, "validation")

    names = [n for n in report["models"] if not n.startswith("baseline")]
    probas = {n: joblib.load(MODEL_DIR / f"{n}_h{horizon}d.joblib").predict_proba(X_val)[:, 1] for n in names}
    baselines = {n: m["validation_metrics"]["confusion_matrix"]
                 for n, m in report["models"].items() if n.startswith("baseline")}
    payload = build_payload(horizon, y_val, probas, baselines)
    write(payload)
    logger.info("wrote %s: %d rows, models %s", output_path(horizon), payload["n_validation"], names)


if __name__ == "__main__":
    main()
