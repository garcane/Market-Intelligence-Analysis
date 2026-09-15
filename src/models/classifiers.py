"""The four baseline classifiers (Stage 9), each wrapped with the shared
preprocessor so every model sees identically-prepared data — important for a
fair comparison in Stage 9's leaderboard.
"""
from __future__ import annotations

from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from src.models.dataset import build_preprocessor

RANDOM_STATE = 42


def build_models() -> dict[str, Pipeline]:
    return {
        "logistic_regression": Pipeline([
            ("preprocessor", build_preprocessor()),
            ("model", LogisticRegression(max_iter=2000, random_state=RANDOM_STATE)),
        ]),
        # Regularized more heavily than a first pass (max_depth 8->4,
        # min_samples_leaf 5->30): the first attempt showed train PR-AUC
        # 0.88 vs validation 0.40 (a 0.48 gap) — clear overfitting on a
        # ~2,800-row training set, not the leakage pattern (validation itself
        # wasn't suspiciously high). See MODELS.md for the before/after.
        "random_forest": Pipeline([
            ("preprocessor", build_preprocessor()),
            ("model", RandomForestClassifier(
                n_estimators=300, max_depth=4, min_samples_split=40, min_samples_leaf=30,
                max_features="sqrt", random_state=RANDOM_STATE, n_jobs=-1,
            )),
        ]),
        # First pass: train PR-AUC 0.976 vs validation 0.406 (0.57 gap).
        # Regularized: shallower trees, stronger L2, more conservative learning rate.
        "xgboost": Pipeline([
            ("preprocessor", build_preprocessor()),
            ("model", XGBClassifier(
                n_estimators=200, max_depth=2, learning_rate=0.03, subsample=0.7,
                colsample_bytree=0.7, min_child_weight=20, reg_lambda=5.0,
                eval_metric="logloss", random_state=RANDOM_STATE, n_jobs=-1,
            )),
        ]),
        # First pass: train PR-AUC 0.957 vs validation 0.413 (0.54 gap).
        "hist_gradient_boosting": Pipeline([
            ("preprocessor", build_preprocessor()),
            ("model", HistGradientBoostingClassifier(
                max_iter=150, max_depth=3, learning_rate=0.03, l2_regularization=5.0,
                min_samples_leaf=30, random_state=RANDOM_STATE,
            )),
        ]),
    }
