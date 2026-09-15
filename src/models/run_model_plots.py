"""Stage 13 (model visualizations): ROC curves, PR curves, and confusion
matrices for the Stage 9 models — the model_report JSON has the numbers,
this script is the missing chart layer over it.
Run as: python -m src.models.run_model_plots
"""
from __future__ import annotations

import logging

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import ConfusionMatrixDisplay, PrecisionRecallDisplay, RocCurveDisplay

from src.config import OUTPUTS_DIR, PROCESSED_DIR
from src.features.target import PRIMARY_HORIZON
from src.models.dataset import build_dataset_for_horizon, split_xy

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL_DIR = OUTPUTS_DIR / "model_results" / "models"
FIGURES_DIR = OUTPUTS_DIR / "figures"
MODEL_NAMES = ["logistic_regression", "random_forest", "xgboost", "hist_gradient_boosting"]


def main(horizon: int = PRIMARY_HORIZON) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    ml_dataset = pd.read_parquet(PROCESSED_DIR / "ml_dataset" / "ml_dataset.parquet")
    prepared, _ = build_dataset_for_horizon(ml_dataset, horizon)
    X_val, y_val = split_xy(prepared, "validation")

    pipelines = {name: joblib.load(MODEL_DIR / f"{name}_h{horizon}d.joblib") for name in MODEL_NAMES}

    # --- ROC curves, all 4 models on one axes ---
    fig, ax = plt.subplots(figsize=(7, 7))
    for name, pipeline in pipelines.items():
        RocCurveDisplay.from_estimator(pipeline, X_val, y_val, name=name, ax=ax)
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="chance")
    ax.set_title(f"ROC Curves — Validation (horizon={horizon}d)")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "13_roc_curves.png", dpi=110)
    plt.close(fig)

    # --- PR curves, all 4 models on one axes ---
    fig, ax = plt.subplots(figsize=(7, 7))
    for name, pipeline in pipelines.items():
        PrecisionRecallDisplay.from_estimator(pipeline, X_val, y_val, name=name, ax=ax)
    baseline_rate = float(y_val.mean())
    ax.axhline(baseline_rate, linestyle="--", color="gray", label=f"baseline (positive rate={baseline_rate:.2f})")
    ax.set_title(f"Precision-Recall Curves — Validation (horizon={horizon}d)")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "13_pr_curves.png", dpi=110)
    plt.close(fig)

    # --- confusion matrices, small multiples ---
    fig, axes = plt.subplots(2, 2, figsize=(10, 9))
    for ax, (name, pipeline) in zip(axes.ravel(), pipelines.items()):
        y_pred = pipeline.predict(X_val)
        ConfusionMatrixDisplay.from_predictions(y_val, y_pred, ax=ax, colorbar=False)
        ax.set_title(name)
    plt.suptitle(f"Confusion Matrices — Validation (horizon={horizon}d, threshold=0.5)")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "13_confusion_matrices.png", dpi=110)
    plt.close(fig)

    logger.info("Stage 13 model plots written to %s", FIGURES_DIR)


if __name__ == "__main__":
    main()
