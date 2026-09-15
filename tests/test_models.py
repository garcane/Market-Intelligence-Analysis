import numpy as np
import pandas as pd

from src.models.baselines import majority_class_predictions, random_predictions
from src.models.classifiers import build_models
from src.models.dataset import build_dataset_for_horizon, get_feature_columns, impute_sparse_features
from src.models.evaluate import calibration_curve_summary, compute_metrics


def _ml_dataset_row(market_id, date, split_5d, target_5d, **overrides):
    row = {
        "market_id": market_id, "date": date, "split_5d": split_5d, "target_5d": target_5d,
        "return_1d": 0.01, "log_return_1d": 0.01, "rolling_vol_7d": 0.02, "rolling_vol_30d": 0.02,
        "drawdown": -0.05, "lag_return_1d": 0.01, "lag_return_3d": 0.01, "lag_return_5d": 0.01,
        "lag_return_10d": 0.01, "rolling_return_5d": 0.02, "rolling_return_10d": 0.03,
        "rolling_return_30d": 0.05, "momentum_10d": 0.01, "momentum_30d": 0.02, "rsi_14d": 55.0,
        "volume_change_1d": 0.1, "volume_ratio_10d": 0.05,
        "market_return": 0.005, "ai_index_return": 0.006, "relative_performance": 0.005,
        "sentiment_current": np.nan, "lag_sentiment_1d": np.nan, "lag_sentiment_3d": np.nan,
        "lag_sentiment_5d": np.nan, "rolling_mean_sentiment_7d": np.nan, "sentiment_volatility": np.nan,
        "positive_ratio": np.nan, "negative_ratio": np.nan, "news_volume": 0.0,
        "sector_return": np.nan, "relative_sector_performance": np.nan,
    }
    row.update(overrides)
    return row


def _synthetic_ml_dataset(n=200, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        split = "train" if i < 140 else ("validation" if i < 180 else "test")
        rows.append(_ml_dataset_row(
            "TEST", pd.Timestamp("2024-01-01") + pd.Timedelta(days=i), split,
            target_5d=float(rng.integers(0, 2)),
            return_1d=float(rng.normal(0, 0.02)),
        ))
    return pd.DataFrame(rows)


class TestDataset:
    def test_impute_sparse_features_adds_missing_flag(self):
        df = pd.DataFrame({"sentiment_current": [0.5, np.nan, -0.3]})
        result = impute_sparse_features(df, sparse_cols=["sentiment_current"])
        assert result["sentiment_current_missing"].tolist() == [0, 1, 0]
        assert result["sentiment_current"].tolist() == [0.5, 0.0, -0.3]

    def test_build_dataset_for_horizon_excludes_non_usable_splits(self):
        df = _synthetic_ml_dataset()
        df.loc[0, "split_5d"] = "excluded_embargo"
        prepared, _ = build_dataset_for_horizon(df, horizon=5)
        assert "excluded_embargo" not in prepared["split"].values

    def test_build_dataset_drops_warmup_rows_with_dense_nan(self):
        df = _synthetic_ml_dataset()
        df.loc[0, "return_1d"] = np.nan  # simulates a warm-up row
        prepared, dropped = build_dataset_for_horizon(df, horizon=5)
        assert dropped == 1
        assert len(prepared) == len(df) - 1

    def test_feature_columns_never_include_raw_price_levels(self):
        numeric, categorical = get_feature_columns()
        for leaky_col in ["close", "open", "high", "low", "volume", "adj_close", "market_cap", "sma_10d"]:
            assert leaky_col not in numeric, f"{leaky_col} is a non-stationary raw level and must not be a feature"

    def test_feature_columns_exclude_target_and_split_columns(self):
        numeric, categorical = get_feature_columns()
        all_cols = numeric + categorical
        for leaky_col in ["target_5d", "future_return_5d", "target_date_5d", "split_5d", "y"]:
            assert leaky_col not in all_cols


class TestEvaluate:
    def test_compute_metrics_basic_shape(self):
        y_true = np.array([0, 1, 1, 0, 1])
        y_pred = np.array([0, 1, 0, 0, 1])
        y_proba = np.array([0.1, 0.8, 0.4, 0.2, 0.9])
        metrics = compute_metrics(y_true, y_pred, y_proba)
        for key in ["accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc",
                    "balanced_accuracy", "specificity", "confusion_matrix"]:
            assert key in metrics

    def test_perfect_predictions_score_perfectly(self):
        y_true = np.array([0, 1, 0, 1, 0, 1])
        y_pred = y_true.copy()
        y_proba = y_true.astype(float)
        metrics = compute_metrics(y_true, y_pred, y_proba)
        assert metrics["accuracy"] == 1.0
        assert metrics["f1"] == 1.0

    def test_suspicious_auc_flag_fires_above_threshold(self):
        rng = np.random.default_rng(0)
        n = 200
        y_true = rng.integers(0, 2, n)
        # near-perfect separation -> very high AUC
        y_proba = y_true.astype(float) * 0.9 + rng.uniform(0, 0.05, n)
        y_pred = (y_proba >= 0.5).astype(int)
        metrics = compute_metrics(y_true, y_pred, y_proba)
        assert metrics["suspiciously_high_auc"]

    def test_suspicious_auc_flag_does_not_fire_for_near_random(self):
        rng = np.random.default_rng(0)
        n = 200
        y_true = rng.integers(0, 2, n)
        y_proba = rng.uniform(0, 1, n)  # unrelated to y_true
        y_pred = (y_proba >= 0.5).astype(int)
        metrics = compute_metrics(y_true, y_pred, y_proba)
        assert not metrics["suspiciously_high_auc"]

    def test_calibration_curve_bins_correctly(self):
        y_true = np.array([0, 0, 1, 1, 1])
        y_proba = np.array([0.05, 0.15, 0.85, 0.9, 0.95])
        curve = calibration_curve_summary(y_true, y_proba, n_bins=10)
        assert all("mean_predicted" in row and "actual_positive_rate" in row for row in curve)


class TestBaselines:
    def test_majority_class_predicts_constant(self):
        y_train = np.array([1, 1, 1, 0])  # 75% positive
        y_pred, y_proba = majority_class_predictions(y_train, n=5)
        assert (y_pred == 1).all()
        assert np.allclose(y_proba, 0.75)

    def test_random_baseline_respects_train_base_rate_approximately(self):
        y_train = np.array([1] * 80 + [0] * 20)  # 80% positive
        y_pred, _ = random_predictions(y_train, n=5000, seed=1)
        assert 0.7 < y_pred.mean() < 0.9  # loosely centered on 0.8


class TestClassifiers:
    def test_build_models_returns_four_pipelines_that_fit_and_predict(self):
        rng = np.random.default_rng(0)
        n = 100
        numeric, categorical = get_feature_columns()
        X = pd.DataFrame({c: rng.normal(0, 1, n) for c in numeric})
        X["market_id"] = rng.choice(["A", "B"], n)
        y = rng.integers(0, 2, n)

        models = build_models()
        assert set(models.keys()) == {"logistic_regression", "random_forest", "xgboost", "hist_gradient_boosting"}
        for name, pipeline in models.items():
            pipeline.fit(X, y)
            proba = pipeline.predict_proba(X)[:, 1]
            assert len(proba) == n
            assert ((proba >= 0) & (proba <= 1)).all()
