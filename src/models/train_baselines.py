"""Stage 9 orchestrator: trains the 4 baseline classifiers plus naive
baselines on the primary horizon, following the target spec's training loop
(prepare -> fit preprocessing on train only -> transform validation -> train
-> probabilities -> classifications -> metrics -> confusion matrix -> class
balance -> calibration -> suspicious-performance check -> compare to
baseline), and produces the model leaderboard using criteria fixed in
src/models/evaluate.py before this script ever ran a model.
Run as: python -m src.models.train_baselines
"""
from __future__ import annotations

import json
import logging
import time

import joblib
import pandas as pd

from src.config import OUTPUTS_DIR, PROCESSED_DIR
from src.features.target import PRIMARY_HORIZON
from src.models.baselines import majority_class_predictions, random_predictions
from src.models.classifiers import build_models
from src.models.dataset import build_dataset_for_horizon, split_xy
from src.models.evaluate import LEADERBOARD_CRITERIA, calibration_curve_summary, compute_metrics
from src.models import validation_predictions

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL_DIR = OUTPUTS_DIR / "model_results" / "models"


def main(horizon: int = PRIMARY_HORIZON) -> None:
    ml_dataset_path = PROCESSED_DIR / "ml_dataset" / "ml_dataset.parquet"
    if not ml_dataset_path.exists():
        raise FileNotFoundError("run src.models.run_split first")
    ml_dataset = pd.read_parquet(ml_dataset_path)

    prepared, n_dropped_warmup = build_dataset_for_horizon(ml_dataset, horizon)
    logger.info("horizon=%dd: %d rows after dropping %d warm-up row(s)", horizon, len(prepared), n_dropped_warmup)

    X_train, y_train = split_xy(prepared, "train")
    X_val, y_val = split_xy(prepared, "validation")
    logger.info("train=%d rows (%.1f%% positive), validation=%d rows (%.1f%% positive)",
                len(y_train), 100 * y_train.mean(), len(y_val), 100 * y_val.mean())

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    report = {"horizon": horizon, "n_train": len(y_train), "n_validation": len(y_val),
              "train_positive_rate": float(y_train.mean()), "val_positive_rate": float(y_val.mean()),
              "models": {}}

    # --- naive baselines (fit "on train" trivially: just the train positive rate) ---
    for name, fn in [("baseline_majority_class", majority_class_predictions),
                      ("baseline_random", random_predictions)]:
        y_pred, y_proba = fn(y_train, len(y_val))
        metrics = compute_metrics(y_val, y_pred, y_proba)
        report["models"][name] = {"validation_metrics": metrics}
        logger.info("%s: val PR-AUC=%.3f ROC-AUC=%.3f F1=%.3f",
                    name, metrics["pr_auc"], metrics["roc_auc"], metrics["f1"])

    # --- the four real models ---
    models = build_models()
    val_probas = {}
    for name, pipeline in models.items():
        t0 = time.perf_counter()
        pipeline.fit(X_train, y_train)  # preprocessing (scaler/encoder) is fit ONLY on train, inside the Pipeline
        train_time = time.perf_counter() - t0

        t0 = time.perf_counter()
        train_proba = pipeline.predict_proba(X_train)[:, 1]
        val_proba = pipeline.predict_proba(X_val)[:, 1]
        inference_time = time.perf_counter() - t0

        train_pred = (train_proba >= 0.5).astype(int)
        val_pred = (val_proba >= 0.5).astype(int)

        train_metrics = compute_metrics(y_train, train_pred, train_proba)
        val_metrics = compute_metrics(y_val, val_pred, val_proba)
        calibration = calibration_curve_summary(y_val, val_proba)
        val_probas[name] = val_proba

        report["models"][name] = {
            "train_metrics": train_metrics,
            "validation_metrics": val_metrics,
            "calibration_validation": calibration,
            "train_time_seconds": round(train_time, 3),
            "inference_time_seconds": round(inference_time, 4),
            # a model that fits train near-perfectly but degrades sharply on
            # validation is overfitting — flagged explicitly, not left implicit.
            "train_val_pr_auc_gap": round(train_metrics["pr_auc"] - val_metrics["pr_auc"], 4),
        }

        joblib.dump(pipeline, MODEL_DIR / f"{name}_h{horizon}d.joblib")

        flag = " *** SUSPICIOUSLY HIGH AUC — INVESTIGATE LEAKAGE ***" if val_metrics["suspiciously_high_auc"] else ""
        logger.info("%s: val PR-AUC=%.3f ROC-AUC=%.3f F1=%.3f train_time=%.2fs%s",
                    name, val_metrics["pr_auc"], val_metrics["roc_auc"], val_metrics["f1"], train_time, flag)

    # --- leaderboard: fixed criteria, defined in evaluate.py before this ran ---
    real_models = [m for m in models]
    leaderboard = sorted(
        real_models,
        key=lambda name: tuple(
            -report["models"][name]["validation_metrics"][c] if c != "brier_score"
            else report["models"][name]["validation_metrics"][c]
            for c in LEADERBOARD_CRITERIA
        ),
    )
    report["leaderboard_criteria"] = LEADERBOARD_CRITERIA
    report["leaderboard"] = leaderboard
    report["any_suspiciously_high_auc"] = any(
        report["models"][m]["validation_metrics"]["suspiciously_high_auc"] for m in real_models
    )

    with open(PROCESSED_DIR / f"model_report_h{horizon}d.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    # per-row validation predictions for the web app's curves and threshold slider
    baselines = {n: m["validation_metrics"]["confusion_matrix"]
                 for n, m in report["models"].items() if n.startswith("baseline")}
    validation_predictions.write(validation_predictions.build_payload(horizon, y_val, val_probas, baselines))

    logger.info("Stage 9 leaderboard (horizon=%dd, ranked by %s): %s", horizon, LEADERBOARD_CRITERIA, leaderboard)
    if report["any_suspiciously_high_auc"]:
        logger.warning("At least one model exceeded the suspicious-AUC threshold — see model_report for detail.")


if __name__ == "__main__":
    main()
