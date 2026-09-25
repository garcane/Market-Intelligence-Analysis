import numpy as np
import pandas as pd

from src.models.ablation import EXPERIMENTS, run_ablation
from src.models.dataset import get_feature_columns


def _synthetic_ml_dataset(n_per_asset=250, seed=0):
    rng = np.random.default_rng(seed)
    numeric, categorical = get_feature_columns()
    assets = ["NVDA", "MSFT"]
    rows = []
    for asset in assets:
        for i in range(n_per_asset):
            row = {c: rng.normal(0, 1) for c in numeric}
            row["market_id"] = asset
            row["date"] = pd.Timestamp("2024-01-01") + pd.Timedelta(days=i)
            row["split_5d"] = "train" if i < 180 else "validation"
            row["target_5d"] = float(rng.integers(0, 2))
            rows.append(row)
    return pd.DataFrame(rows)


class TestAblationExperiments:
    def test_four_experiments_defined(self):
        assert len(EXPERIMENTS) == 4
        assert set(EXPERIMENTS.keys()) == {
            "A_market_only", "B_sentiment_only", "C_market_plus_sentiment",
            "D_market_plus_sentiment_plus_crosssectional",
        }

    def test_experiment_feature_sets_nest_correctly(self):
        # C should be a superset of A and B's own feature groups; D a superset of C
        a, b, c, d = (set(EXPERIMENTS[k]) for k in
                      ["A_market_only", "B_sentiment_only", "C_market_plus_sentiment",
                       "D_market_plus_sentiment_plus_crosssectional"])
        assert a.issubset(c)
        assert b.issubset(c)
        assert c.issubset(d)

    def test_market_only_and_sentiment_only_are_disjoint(self):
        a = set(EXPERIMENTS["A_market_only"])
        b = set(EXPERIMENTS["B_sentiment_only"])
        assert a.isdisjoint(b)

    def test_run_ablation_produces_metrics_for_every_experiment(self):
        ml_dataset = _synthetic_ml_dataset()
        results = run_ablation(ml_dataset, horizon=5)
        assert set(results.keys()) == set(EXPERIMENTS.keys())
        for exp_name, metrics in results.items():
            assert "pr_auc" in metrics
            assert 0 <= metrics["pr_auc"] <= 1
            assert metrics["n_train"] > 0

    def test_run_ablation_uses_fewer_features_in_a_and_b_than_d(self):
        ml_dataset = _synthetic_ml_dataset()
        results = run_ablation(ml_dataset, horizon=5)
        assert results["A_market_only"]["n_features"] < results["D_market_plus_sentiment_plus_crosssectional"]["n_features"]
        assert results["B_sentiment_only"]["n_features"] < results["D_market_plus_sentiment_plus_crosssectional"]["n_features"]
