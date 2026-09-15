"""Naive baselines the four real models must beat to be worth anything.
Rule 5 of the target spec: a model isn't "good" just because a metric looks
high — comparing against a trivial majority-class predictor is how a metric
like accuracy gets caught being meaningless on an imbalanced-enough target.
"""
from __future__ import annotations

import numpy as np


def majority_class_predictions(y_train: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    majority = int(np.round(y_train.mean())) if len(y_train) else 0
    y_pred = np.full(n, majority)
    y_proba = np.full(n, float(y_train.mean()) if len(y_train) else 0.5)
    return y_pred, y_proba


def random_predictions(y_train: np.ndarray, n: int, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    positive_rate = float(y_train.mean()) if len(y_train) else 0.5
    y_proba = rng.uniform(0, 1, n)
    y_pred = (rng.uniform(0, 1, n) < positive_rate).astype(int)
    return y_pred, y_proba
