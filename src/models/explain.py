"""Stage 10: feature importance & explainability. Every function here returns
*predictive* importance (which features the model actually uses to
discriminate), never framed as causal — the target spec is explicit that these
are different things and must not be conflated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance


def get_feature_names(pipeline) -> list[str]:
    return list(pipeline.named_steps["preprocessor"].get_feature_names_out())


def tree_feature_importance(pipeline) -> pd.DataFrame:
    """Built-in impurity/gain-based importance for tree models."""
    names = get_feature_names(pipeline)
    model = pipeline.named_steps["model"]
    importances = model.feature_importances_
    return pd.DataFrame({"feature": names, "importance": importances}).sort_values(
        "importance", ascending=False).reset_index(drop=True)


def lr_coefficients(pipeline) -> pd.DataFrame:
    """Standardized coefficients (features were scaled by the pipeline's
    StandardScaler, so these are directly comparable in magnitude, unlike raw
    coefficients on unscaled features)."""
    names = get_feature_names(pipeline)
    coefs = pipeline.named_steps["model"].coef_[0]
    return pd.DataFrame({"feature": names, "coefficient": coefs,
                          "abs_coefficient": np.abs(coefs)}).sort_values(
        "abs_coefficient", ascending=False).reset_index(drop=True)


def compute_permutation_importance(pipeline, X_val: pd.DataFrame, y_val: np.ndarray,
                                    n_repeats: int = 10, random_state: int = 42,
                                    scoring: str = "average_precision") -> pd.DataFrame:
    """Model-agnostic: measures the drop in validation PR-AUC when each raw
    input column is shuffled. Works identically for every model type (unlike
    tree importances or LR coefficients, which are model-specific), so this
    is the fairest way to compare signal across all four models.
    """
    result = permutation_importance(pipeline, X_val, y_val, n_repeats=n_repeats,
                                     random_state=random_state, scoring=scoring, n_jobs=-1)
    return pd.DataFrame({
        "feature": X_val.columns,
        "importance_mean": result.importances_mean,
        "importance_std": result.importances_std,
    }).sort_values("importance_mean", ascending=False).reset_index(drop=True)


def compute_shap_values(pipeline, X_sample: pd.DataFrame, model_type: str) -> pd.DataFrame:
    """Mean absolute SHAP value per feature on a sample of rows (SHAP is
    expensive; a sample keeps this practical, per the spec's "where
    practical"). `model_type` selects TreeExplainer (tree models) or
    LinearExplainer (logistic regression).
    """
    import shap

    preprocessor = pipeline.named_steps["preprocessor"]
    model = pipeline.named_steps["model"]
    names = get_feature_names(pipeline)
    X_transformed = preprocessor.transform(X_sample)
    if hasattr(X_transformed, "toarray"):
        X_transformed = X_transformed.toarray()

    if model_type == "linear":
        explainer = shap.LinearExplainer(model, X_transformed)
    else:
        explainer = shap.TreeExplainer(model)

    shap_values = explainer.shap_values(X_transformed)
    if isinstance(shap_values, list):  # some tree explainers return per-class list
        shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
    shap_values = np.asarray(shap_values)
    if shap_values.ndim == 3:  # (n_samples, n_features, n_classes)
        shap_values = shap_values[:, :, 1]

    mean_abs = np.abs(shap_values).mean(axis=0)
    return pd.DataFrame({"feature": names, "mean_abs_shap": mean_abs}).sort_values(
        "mean_abs_shap", ascending=False).reset_index(drop=True)


def compare_top_features(importance_frames: dict[str, pd.DataFrame], top_n: int = 10) -> pd.DataFrame:
    """For each model's importance ranking, extract its top-N features and
    report how many models agree a given feature belongs in their own top-N —
    a simple, interpretable cross-model agreement measure. `importance_frames`
    maps model name -> a DataFrame with a 'feature' column ordered by importance.
    """
    top_sets = {name: set(df["feature"].head(top_n)) for name, df in importance_frames.items()}
    all_features = sorted(set().union(*top_sets.values()))
    rows = []
    for feature in all_features:
        agreement = sum(feature in s for s in top_sets.values())
        rows.append({"feature": feature, "n_models_in_top_n": agreement,
                     "models": [name for name, s in top_sets.items() if feature in s]})
    return pd.DataFrame(rows).sort_values("n_models_in_top_n", ascending=False).reset_index(drop=True)
