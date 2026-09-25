"""End-to-end pipeline integration test (target spec 27: "Pipeline: end-to-end
execution succeeds"). Every other test file in this suite tests one module in
isolation against hand-shaped fixtures — which proves each module is correct
on its own, but would NOT catch a schema mismatch at the boundary BETWEEN two
stages (e.g. one stage renaming a column the next stage still expects by the
old name — exactly the class of bug found and fixed mid-session in the merged
ingestion architecture, see CHECKPOINT.md's "Interim" entry).

This test runs real data through the real stage functions — sentiment scoring
-> feature engineering -> target construction -> temporal split -> dataset
prep -> model fit/predict — entirely offline (synthetic OHLCV/news, no
network), so it's fast enough to run on every commit while still exercising
genuine inter-stage integration, not mocks.
"""
import numpy as np
import pandas as pd

from src.features.pipeline import build_all_features
from src.features.target import build_target_table
from src.models.classifiers import build_models
from src.models.dataset import build_dataset_for_horizon, split_xy
from src.models.split import add_split_labels
from src.sentiment.score import score_news


def _synthetic_market_prices(market_ids, n=150, seed=0):
    rng = np.random.default_rng(seed)
    prices = {}
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    for i, mid in enumerate(market_ids):
        close = 100 * np.cumprod(1 + rng.normal(0.0005, 0.02, n))
        high = close * (1 + np.abs(rng.normal(0, 0.005, n)))
        low = close * (1 - np.abs(rng.normal(0, 0.005, n)))
        open_ = close * (1 + rng.normal(0, 0.003, n))
        volume = rng.integers(1_000_000, 5_000_000, n).astype(float)
        prices[mid] = pd.DataFrame({
            "date": dates, "open": open_, "high": high, "low": low,
            "close": close, "volume": volume,
        })
    return prices


def _synthetic_news(market_ids, ticker_to_company_id, n_per_asset=20, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    dates = pd.date_range("2024-01-10", periods=80, freq="D")
    headlines_pos = ["Company reports record profits and stock surges",
                      "Strong earnings beat drives shares higher"]
    headlines_neg = ["Company faces lawsuit as stock crashes",
                      "Shares plunge on disappointing guidance"]
    for i, mid in enumerate(market_ids):
        for j in range(n_per_asset):
            ts = dates[rng.integers(0, len(dates))]
            title = rng.choice(headlines_pos if j % 2 == 0 else headlines_neg)
            rows.append({
                "news_id": f"{mid}_{j}",
                "timestamp": ts,
                "source_id": "test_source",
                "title": title,
                "description": None,
                "url": f"http://example.com/{mid}/{j}",
                "matched_company_id": ticker_to_company_id.get(mid),
                "matched_asset_id": None,
                "category": "general",
            })
    return pd.DataFrame(rows)


class TestFullPipelineIntegration:
    # Real tickers already in data/reference/companies.csv (NVDA is "equity" +
    # "AI category" tagged; MU has no AI-category tag but is still "equity")
    # — using real market_ids (with synthetic, in-memory-only price series,
    # never touching the real ingested data/raw parquet files) matters
    # because ai_index_return/sector_return are computed against the Stage 1
    # universe reference tables, not against whatever tickers happen to be in
    # a given batch — a fully-fabricated ticker name would never match that
    # universe and would make every cross-sectional feature NaN, which is
    # correct pipeline behavior but not what this test is meant to exercise.
    REAL_MARKET_IDS = ["NVDA", "MU"]
    TICKER_TO_COMPANY_ID = {"NVDA": "nvidia", "MU": "micron"}  # from data/reference/companies.csv

    def test_ingestion_output_flows_through_sentiment_to_features_to_target_to_split_to_model(self):
        market_ids = self.REAL_MARKET_IDS
        market_prices = _synthetic_market_prices(market_ids)
        news_df = _synthetic_news(market_ids, self.TICKER_TO_COMPANY_ID)

        # --- Stage 4: sentiment scoring ---
        sentiment_df = score_news(news_df)
        assert set(sentiment_df.columns) == {"news_id", "sentiment_model", "sentiment_score",
                                              "sentiment_label", "scored_at"}
        assert sentiment_df["sentiment_score"].between(-1, 1).all()

        # --- Stage 6: features (requires src.ingestion.universe.entity_to_market_map
        # and company_ai_categories to resolve — uses the real reference tables, so
        # this also implicitly checks the synthetic market_ids don't crash that path
        # by simply not matching any real entity, which is the realistic case here) ---
        features = build_all_features(market_prices, sentiment_df, news_df)
        assert set(market_ids) == set(features["market_id"].unique())
        assert not features.duplicated(subset=["market_id", "date"]).any()

        # --- Stage 7: target ---
        targets = build_target_table(market_prices, horizons=(5,), threshold=0.02)
        assert set(market_ids) == set(targets["market_id"].unique())

        # --- merge (mirrors src.models.run_split's own integration point) ---
        merged = features.merge(targets, on=["market_id", "date"], how="inner", validate="one_to_one")
        assert len(merged) == len(features), "feature/target merge dropped rows — schema drift between stages"

        # --- Stage 8: split ---
        split_boundary_start = merged["date"].quantile(0.6)
        split_boundary_end = merged["date"].quantile(0.8)
        merged = add_split_labels(merged, horizons=(5,),
                                   train_end=str(pd.Timestamp(split_boundary_start).date()),
                                   val_end=str(pd.Timestamp(split_boundary_end).date()))
        assert "split_5d" in merged.columns
        assert set(merged["split_5d"].unique()).issubset(
            {"train", "validation", "test", "excluded_embargo", "excluded_no_target"})

        # --- Stage 9: dataset prep + model fit/predict ---
        prepared, _dropped = build_dataset_for_horizon(merged, horizon=5)
        X_train, y_train = split_xy(prepared, "train")
        X_val, y_val = split_xy(prepared, "validation")
        assert len(X_train) > 0, "no training rows survived the full pipeline — integration broke somewhere upstream"
        assert len(X_val) > 0, "no validation rows survived the full pipeline"

        model = build_models()["logistic_regression"]
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_val)[:, 1]
        assert len(proba) == len(X_val)
        assert ((proba >= 0) & (proba <= 1)).all()

    def test_pipeline_is_idempotent_when_run_twice(self):
        # regression guard: running the same inputs through the same functions
        # twice must produce identical output (no hidden global state, no
        # randomness without a fixed seed anywhere in the chain).
        market_ids = ["NVDA"]
        market_prices = _synthetic_market_prices(market_ids)
        news_df = _synthetic_news(market_ids, {"NVDA": "nvidia"})
        sentiment_df = score_news(news_df)

        features_1 = build_all_features(market_prices, sentiment_df, news_df)
        features_2 = build_all_features(market_prices, sentiment_df, news_df)
        pd.testing.assert_frame_equal(features_1, features_2)

    def test_sparse_columns_survive_when_no_asset_in_batch_has_a_match(self):
        # Regression test for a real bug this integration test found: when
        # NO asset in a batch resolves to a matched sentiment entity or a
        # sector membership (e.g. a fabricated ticker name, or — in
        # production — a batch of assets added before any news/category
        # coverage exists for them), the sparse feature columns
        # (sentiment_*, sector_return, relative_sector_performance) used to
        # be entirely ABSENT from the feature table rather than present-with-
        # NaN, which crashed src/models/dataset.py::impute_sparse_features
        # with a KeyError. Fixed by having impute_sparse_features create
        # missing sparse columns as NaN before imputing, rather than assuming
        # the upstream feature pipeline always produced them.
        from src.models.dataset import SPARSE_FEATURES, impute_sparse_features

        market_ids = ["FAKE_A", "FAKE_B"]  # deliberately not in companies.csv/crypto_assets.csv
        market_prices = _synthetic_market_prices(market_ids)
        news_df = _synthetic_news(market_ids, ticker_to_company_id={})  # no entity matches at all
        sentiment_df = score_news(news_df)

        features = build_all_features(market_prices, sentiment_df, news_df)
        # No asset has a sector match. The columns used to be absent here; the
        # producer now guarantees them as all-NaN float columns.
        assert "sector_return" in features.columns
        assert features["sector_return"].isna().all()

        imputed = impute_sparse_features(features, sparse_cols=SPARSE_FEATURES)
        for col in SPARSE_FEATURES:
            assert col in imputed.columns
            assert f"{col}_missing" in imputed.columns
            assert imputed[col].isna().sum() == 0  # fully imputed, no crash, no leftover NaN

    def test_feature_schema_is_stable_without_any_sentiment_data(self):
        from src.features.pipeline import SECTOR_FEATURE_COLUMNS
        from src.features.sentiment_features import SENTIMENT_FEATURE_COLUMNS

        features = build_all_features(_synthetic_market_prices(["FAKE_A"]), None, None)
        for col in SENTIMENT_FEATURE_COLUMNS + SECTOR_FEATURE_COLUMNS:
            assert col in features.columns, f"{col} missing from feature schema"
            assert pd.api.types.is_float_dtype(features[col]), f"{col} is not float"
