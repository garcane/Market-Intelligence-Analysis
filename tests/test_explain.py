import numpy as np
import pandas as pd

from src.models.classifiers import build_models
from src.models.dataset import get_feature_columns
from src.models.explain import (
    compare_top_features,
    compute_permutation_importance,
    lr_coefficients,
    tree_feature_importance,
)


def _fitted_models(n=300, seed=0):
    rng = np.random.default_rng(seed)
    numeric, categorical = get_feature_columns()
    X = pd.DataFrame({c: rng.normal(0, 1, n) for c in numeric})
    X["market_id"] = rng.choice(["A", "B", "C"], n)
    # make one feature (the first numeric column) genuinely predictive so
    # importance methods have a real, verifiable signal to recover
    signal_col = numeric[0]
    y = (X[signal_col] + rng.normal(0, 0.5, n) > 0).astype(int).values
    models = build_models()
    for pipeline in models.values():
        pipeline.fit(X, y)
    return models, X, y, signal_col


class TestTreeAndLRImportance:
    def test_tree_importance_ranks_the_real_signal_highly(self):
        models, X, y, signal_col = _fitted_models()
        imp = tree_feature_importance(models["random_forest"])
        top_5 = imp["feature"].head(5).tolist()
        assert any(signal_col in f for f in top_5)

    def test_lr_coefficients_have_expected_sign(self):
        models, X, y, signal_col = _fitted_models()
        coefs = lr_coefficients(models["logistic_regression"])
        signal_row = coefs[coefs["feature"] == f"numeric__{signal_col}"]
        assert not signal_row.empty
        assert signal_row["coefficient"].iloc[0] > 0  # y was defined as (signal > 0)

    def test_importance_dataframe_sums_are_sane(self):
        models, X, y, signal_col = _fitted_models()
        imp = tree_feature_importance(models["xgboost"])
        assert (imp["importance"] >= 0).all()
        assert len(imp) == X.shape[1] + 2  # +2 because market_id one-hot expands to 3 columns, -1 for the original


class TestPermutationImportance:
    def test_permutation_importance_identifies_real_signal(self):
        models, X, y, signal_col = _fitted_models()
        perm = compute_permutation_importance(models["logistic_regression"], X, y, n_repeats=5)
        assert perm["feature"].iloc[0] == signal_col  # top feature should be the real signal

    def test_permutation_importance_is_model_agnostic_interface(self):
        # same call signature works for every model type without special-casing
        models, X, y, signal_col = _fitted_models()
        for name, pipeline in models.items():
            perm = compute_permutation_importance(pipeline, X, y, n_repeats=3)
            assert set(perm.columns) == {"feature", "importance_mean", "importance_std"}


class TestCrossModelAgreement:
    def test_agreement_counts_bounded_by_number_of_models(self):
        df_a = pd.DataFrame({"feature": ["x1", "x2", "x3"], "importance": [3, 2, 1]})
        df_b = pd.DataFrame({"feature": ["x1", "x4", "x5"], "importance": [3, 2, 1]})
        agreement = compare_top_features({"model_a": df_a, "model_b": df_b}, top_n=3)
        assert agreement["n_models_in_top_n"].max() <= 2

    def test_feature_in_both_models_top_n_gets_full_agreement(self):
        df_a = pd.DataFrame({"feature": ["x1", "x2"], "importance": [2, 1]})
        df_b = pd.DataFrame({"feature": ["x1", "x3"], "importance": [2, 1]})
        agreement = compare_top_features({"model_a": df_a, "model_b": df_b}, top_n=2)
        x1_row = agreement[agreement["feature"] == "x1"].iloc[0]
        assert x1_row["n_models_in_top_n"] == 2
