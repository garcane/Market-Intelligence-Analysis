"""Stage 10 orchestrator: loads Stage 9's trained models, computes tree/LR
importance, permutation importance, SHAP values, and cross-model agreement.
Run as: python -m src.models.run_explain
"""
from __future__ import annotations

import json
import logging

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.config import OUTPUTS_DIR, PROCESSED_DIR
from src.features.target import PRIMARY_HORIZON
from src.models.dataset import build_dataset_for_horizon, split_xy
from src.models.explain import (
    compare_top_features,
    compute_permutation_importance,
    compute_shap_values,
    lr_coefficients,
    tree_feature_importance,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL_DIR = OUTPUTS_DIR / "model_results" / "models"
FIGURES_DIR = OUTPUTS_DIR / "figures"
SHAP_SAMPLE_SIZE = 300


def _plot_top_features(df: pd.DataFrame, value_col: str, title: str, path, top_n: int = 15) -> None:
    top = df.head(top_n).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top["feature"], top[value_col])
    ax.set_title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close(fig)


def main(horizon: int = PRIMARY_HORIZON) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    ml_dataset_path = PROCESSED_DIR / "ml_dataset" / "ml_dataset.parquet"
    ml_dataset = pd.read_parquet(ml_dataset_path)
    prepared, _ = build_dataset_for_horizon(ml_dataset, horizon)
    X_val, y_val = split_xy(prepared, "validation")

    report = {"horizon": horizon}
    tree_importances = {}

    # HistGradientBoostingClassifier doesn't expose feature_importances_ (a
    # real sklearn limitation, not an oversight) — it's still covered below
    # by permutation importance, which is model-agnostic.
    for name in ["random_forest", "xgboost"]:
        pipeline = joblib.load(MODEL_DIR / f"{name}_h{horizon}d.joblib")
        imp = tree_feature_importance(pipeline)
        tree_importances[name] = imp
        imp.to_csv(PROCESSED_DIR / f"importance_{name}_h{horizon}d.csv", index=False)
        _plot_top_features(imp, "importance", f"{name}: built-in feature importance",
                            FIGURES_DIR / f"10_importance_{name}.png")
        report[f"{name}_top10_importance"] = imp.head(10).to_dict(orient="records")
        logger.info("%s top 5 features: %s", name, imp["feature"].head(5).tolist())

    lr_pipeline = joblib.load(MODEL_DIR / f"logistic_regression_h{horizon}d.joblib")
    lr_coefs = lr_coefficients(lr_pipeline)
    lr_coefs.to_csv(PROCESSED_DIR / f"importance_logistic_regression_h{horizon}d.csv", index=False)
    _plot_top_features(lr_coefs, "abs_coefficient", "Logistic Regression: |standardized coefficient|",
                        FIGURES_DIR / "10_importance_logistic_regression.png")
    report["logistic_regression_top10_coefficients"] = lr_coefs.head(10).to_dict(orient="records")
    logger.info("logistic_regression top 5 |coef| features: %s", lr_coefs["feature"].head(5).tolist())

    # --- permutation importance: the one model-agnostic ranking every model shares ---
    perm_importances = {}
    for name in ["logistic_regression", "random_forest", "xgboost", "hist_gradient_boosting"]:
        pipeline = joblib.load(MODEL_DIR / f"{name}_h{horizon}d.joblib")
        perm = compute_permutation_importance(pipeline, X_val, y_val, n_repeats=5)
        perm_importances[name] = perm
        perm.to_csv(PROCESSED_DIR / f"permutation_importance_{name}_h{horizon}d.csv", index=False)
        logger.info("%s top 5 permutation-importance features: %s", name, perm["feature"].head(5).tolist())

    # --- SHAP (on a validation sample, per model, best-effort) ---
    shap_frames = {}
    sample = X_val.sample(min(SHAP_SAMPLE_SIZE, len(X_val)), random_state=42)
    for name, model_type in [("logistic_regression", "linear"), ("xgboost", "tree"),
                              ("hist_gradient_boosting", None)]:
        if model_type is None:
            continue  # HistGradientBoostingClassifier isn't supported by shap.TreeExplainer in this shap version
        try:
            pipeline = joblib.load(MODEL_DIR / f"{name}_h{horizon}d.joblib")
            shap_df = compute_shap_values(pipeline, sample, model_type)
            shap_frames[name] = shap_df
            shap_df.to_csv(PROCESSED_DIR / f"shap_{name}_h{horizon}d.csv", index=False)
            _plot_top_features(shap_df, "mean_abs_shap", f"{name}: mean |SHAP value|",
                                FIGURES_DIR / f"10_shap_{name}.png")
            logger.info("%s top 5 SHAP features: %s", name, shap_df["feature"].head(5).tolist())
        except Exception as exc:  # noqa: BLE001 - SHAP is "where practical", must not block the stage
            logger.warning("SHAP failed for %s: %s", name, exc)

    # --- cross-model agreement (permutation importance: fair across all 4 model types) ---
    agreement = compare_top_features(perm_importances, top_n=10)
    agreement.to_csv(PROCESSED_DIR / f"feature_agreement_h{horizon}d.csv", index=False)
    report["cross_model_agreement_top_features"] = agreement.head(15).to_dict(orient="records")

    with open(PROCESSED_DIR / f"explainability_report_h{horizon}d.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("Stage 10 explainability complete. Top cross-model-agreed features: %s",
                agreement.head(5)["feature"].tolist())


if __name__ == "__main__":
    main()
