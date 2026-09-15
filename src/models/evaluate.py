"""Model evaluation metrics (Stage 9's training loop + the unlabeled "MODEL
EVALUATION" section of the target spec). Accuracy is never the sole metric —
PR-AUC is the primary ranking criterion (defined here, before any model has
been run, per the spec's instruction not to pick a metric after seeing results).

SUSPICIOUS_AUC_THRESHOLD: if any model clears this on the validation set, the
spec says STOP and investigate leakage rather than celebrate. Every run's
report explicitly says whether this fired.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score, average_precision_score, balanced_accuracy_score,
    brier_score_loss, confusion_matrix, f1_score, precision_score,
    recall_score, roc_auc_score,
)

SUSPICIOUS_AUC_THRESHOLD = 0.90

# Defined before any model is run — see Stage 9's "MODEL COMPARISON LOOP":
# primary criterion first, secondary criteria as tiebreakers, decided before
# results exist, not rationalized afterward.
LEADERBOARD_CRITERIA = ["pr_auc", "roc_auc", "f1", "brier_score"]


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_proba: np.ndarray) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    specificity = tn / (tn + fp) if (tn + fp) else float("nan")

    metrics = {
        "n": len(y_true),
        "positive_rate": float(np.mean(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "specificity": float(specificity),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }

    # ROC-AUC/PR-AUC/Brier need both classes present and a non-degenerate y_proba
    if len(np.unique(y_true)) == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba))
        metrics["pr_auc"] = float(average_precision_score(y_true, y_proba))
        metrics["brier_score"] = float(brier_score_loss(y_true, y_proba))
    else:
        metrics["roc_auc"] = metrics["pr_auc"] = metrics["brier_score"] = float("nan")

    metrics["suspiciously_high_auc"] = bool(
        not np.isnan(metrics["roc_auc"]) and metrics["roc_auc"] >= SUSPICIOUS_AUC_THRESHOLD
    )
    return metrics


def calibration_curve_summary(y_true: np.ndarray, y_proba: np.ndarray, n_bins: int = 10) -> list[dict]:
    """Mean predicted probability vs actual positive rate per probability bin
    — a cheap, inspectable calibration check without extra dependencies."""
    bins = np.linspace(0, 1, n_bins + 1)
    bin_idx = np.digitize(y_proba, bins) - 1
    bin_idx = np.clip(bin_idx, 0, n_bins - 1)
    rows = []
    for b in range(n_bins):
        mask = bin_idx == b
        if not mask.any():
            continue
        rows.append({
            "bin": f"{bins[b]:.1f}-{bins[b+1]:.1f}",
            "n": int(mask.sum()),
            "mean_predicted": float(y_proba[mask].mean()),
            "actual_positive_rate": float(y_true[mask].mean()),
        })
    return rows
