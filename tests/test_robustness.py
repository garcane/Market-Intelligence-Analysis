import numpy as np
import pandas as pd

from src.models.classifiers import build_models
from src.models.dataset import get_feature_columns
from src.models.robustness import CRYPTO_ASSETS, EQUITY_ASSETS, evaluate_by_asset_group, evaluate_across_seeds


def _synthetic_ml_dataset(n_per_asset=300, seed=0):
    rng = np.random.default_rng(seed)
    numeric, categorical = get_feature_columns()
    assets = ["NVDA", "MSFT", "BTC"]
    rows = []
    for asset in assets:
        for i in range(n_per_asset):
            row = {c: rng.normal(0, 1) for c in numeric}
            row["market_id"] = asset
            row["date"] = pd.Timestamp("2024-01-01") + pd.Timedelta(days=i)
            row["split_5d"] = "train" if i < 200 else "validation"
            row["target_5d"] = float(rng.integers(0, 2))
            rows.append(row)
    return pd.DataFrame(rows)


class TestEvaluateByAssetGroup:
    def test_splits_equity_and_crypto_correctly(self):
        numeric, categorical = get_feature_columns()
        rng = np.random.default_rng(0)
        n = 100
        X_val = pd.DataFrame({c: rng.normal(0, 1, n) for c in numeric})
        X_val["market_id"] = ["NVDA"] * 50 + ["BTC"] * 50
        y_val = rng.integers(0, 2, n)

        models = build_models()
        model = models["logistic_regression"]
        # fit on the same shape so predict_proba works
        model.fit(X_val, y_val)

        results = evaluate_by_asset_group(model, X_val, y_val)
        assert "equity" in results and "crypto" in results
        assert results["equity"]["n"] == 50
        assert results["crypto"]["n"] == 50

    def test_equity_and_crypto_sets_are_disjoint(self):
        assert EQUITY_ASSETS.isdisjoint(CRYPTO_ASSETS)

    def test_missing_group_is_simply_absent_not_erroring(self):
        numeric, categorical = get_feature_columns()
        rng = np.random.default_rng(0)
        n = 20
        X_val = pd.DataFrame({c: rng.normal(0, 1, n) for c in numeric})
        X_val["market_id"] = ["NVDA"] * n  # no crypto rows at all
        y_val = rng.integers(0, 2, n)
        model = build_models()["logistic_regression"]
        model.fit(X_val, y_val)
        results = evaluate_by_asset_group(model, X_val, y_val)
        assert "equity" in results
        assert "crypto" not in results


class TestEvaluateAcrossSeeds:
    def test_different_seeds_produce_a_variance_estimate(self):
        ml_dataset = _synthetic_ml_dataset()
        result = evaluate_across_seeds(ml_dataset, model_name="logistic_regression",
                                        horizon=5, seeds=(1, 2, 3))
        assert len(result["pr_auc_by_seed"]) == 3
        assert result["std_pr_auc"] >= 0
        assert "mean_pr_auc" in result

    def test_logistic_regression_is_seed_invariant(self):
        # LogisticRegression's solver is deterministic given the same data
        # (no bootstrap/subsampling), so its own random_state shouldn't move
        # the result at all — a useful contrast against tree ensembles, which
        # genuinely do vary by seed.
        ml_dataset = _synthetic_ml_dataset()
        result = evaluate_across_seeds(ml_dataset, model_name="logistic_regression",
                                        horizon=5, seeds=(1, 2, 3))
        assert result["std_pr_auc"] < 1e-9
