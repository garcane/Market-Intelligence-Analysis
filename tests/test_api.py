"""Web API tests against a small synthetic data directory (data/ is gitignored)."""
import json

import joblib
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import api.data as data
import api.routers.models as models_router
from api.main import create_app
from src.models.classifiers import build_models
from src.models.dataset import (
    ALL_FEATURES,
    CROSS_SECTIONAL_FEATURES,
    MARKET_FEATURES,
    get_feature_columns,
    impute_sparse_features,
)
from src.models.predict import latest_feature_rows, predict_latest

DATES = pd.bdate_range("2024-01-01", periods=60)


def _prices(market_id, seed, source="yahoo_finance"):
    rng = np.random.default_rng(seed)
    close = 100 * np.cumprod(1 + rng.normal(0, 0.01, len(DATES)))
    return pd.DataFrame({"date": DATES, "asset_id": market_id, "open": close, "high": close * 1.01,
                         "low": close * 0.99, "close": close, "adj_close": close, "volume": 1e6,
                         "source": source})


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    market = tmp_path / "market_prices"
    market.mkdir()
    for i, mid in enumerate(["NVDA", "MSFT", "BTC", "SPX"]):
        _prices(mid, i).to_parquet(market / f"{mid}.parquet")
    # TSM's last 10 rows came from a provider whose licence forbids redistribution
    tsm = _prices("TSM", 9)
    tsm.loc[tsm.index[-10:], "source"] = "tiingo"
    tsm.to_parquet(market / "TSM.parquet")

    news = pd.DataFrame({
        "news_id": ["a", "b", "c"],
        "timestamp": pd.to_datetime(["2024-01-02 10:00", "2024-01-03 11:00", "2024-02-01 09:00"]),
        "title": ["Nvidia beats estimates", "Microsoft cloud grows", "Bitcoin slides"],
        "source": ["finnhub", "finnhub", "google_news"], "source_id": ["Reuters", "CNBC", "coindesk"],
        "url": ["https://x/a", "https://x/b", "https://x/c"], "description": ["full text"] * 3,
        "entity": ["NVDA", "MSFT", None], "asset_type": ["equity", "equity", "crypto"],
        "matched_company_id": ["nvidia", "microsoft", None], "matched_asset_id": [None, None, "btc"],
    })
    news_path = tmp_path / "news.parquet"
    news.to_parquet(news_path)
    sent = pd.DataFrame({
        "news_id": ["a", "b", "c", "a", "b", "c"],
        "sentiment_model": ["vader"] * 3 + ["textblob"] * 3,
        "sentiment_score": [0.6, 0.1, -0.5, 0.3, 0.0, -0.2],
        "sentiment_label": ["Bullish", "Neutral", "Bearish", "Slightly Bullish", "Neutral", "Slightly Bearish"],
    })
    sent_path = tmp_path / "sentiment.parquet"
    sent.to_parquet(sent_path)

    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "model_report_h5d.json").write_text(json.dumps({
        "horizon": 5, "leaderboard": ["xgboost"], "any_suspiciously_high_auc": False, "val_positive_rate": 0.4,
        "models": {"xgboost": {"validation_metrics": {"pr_auc": 0.41, "roc_auc": float("nan")}}}}))
    pd.DataFrame({"feature": ["numeric__rsi_14d"], "importance": [0.2]}).to_csv(
        processed / "importance_xgboost_h5d.csv", index=False)
    (processed / "indices_report.json").write_text(json.dumps({"index_members": {}, "indices": {}}))
    (processed / "event_study_report.json").write_text(json.dumps({"benchmark": "SPX", "window": 5, "events": []}))
    pd.DataFrame({"": [-1, 0, 1], "AAR": [0.0, 0.01, 0.0], "CAAR": [0.0, 0.01, 0.01], "n_events": [2, 2, 2]}).to_csv(
        processed / "event_study_caar.csv", index=False)

    figures = tmp_path / "figures"
    figures.mkdir()
    (figures / "13_roc_curves.png").write_bytes(b"\x89PNG fake")
    (tmp_path / "secret.txt").write_text("nope")

    monkeypatch.setattr(data, "MARKET_DIR", market)
    monkeypatch.setattr(data, "NEWS_PATH", news_path)
    monkeypatch.setattr(data, "SENTIMENT_PATH", sent_path)
    monkeypatch.setattr(data, "PROCESSED_DIR", processed)
    monkeypatch.setattr(data, "FIGURES_DIR", figures)
    monkeypatch.setattr(models_router, "MODEL_DIR", tmp_path / "no_models")
    data.clear_cache()
    yield tmp_path
    data.clear_cache()


@pytest.fixture
def local(data_dir):
    return TestClient(create_app("local", web_dist=data_dir / "no_dist"))


@pytest.fixture
def public(data_dir):
    return TestClient(create_app("public", web_dist=data_dir / "no_dist"))


def test_meta_reports_mode_and_freshness(local):
    body = local.get("/api/meta").json()
    assert body["mode"] == "local" and body["pipeline_enabled"] is True
    assert body["latest_price_date"] == str(DATES[-1].date())
    assert body["news_count"] == 3 and body["scored_articles"] == 3


def test_markets_list_has_stats_and_kinds(local):
    rows = {r["market_id"]: r for r in local.get("/api/markets").json()}
    assert set(rows) == {"NVDA", "MSFT", "BTC", "SPX", "TSM"}
    assert rows["BTC"]["kind"] == "crypto" and rows["SPX"]["kind"] == "benchmark" and rows["NVDA"]["kind"] == "equity"
    assert rows["NVDA"]["modelled"] and not rows["SPX"]["modelled"]
    assert {"total_return", "max_drawdown", "annualized_volatility", "spark"} <= set(rows["NVDA"])


def test_prices_filters_range_and_computes_series(local):
    body = local.get("/api/markets/NVDA/prices", params={"start": "2024-02-01"}).json()
    assert body["rows"][0]["date"] >= "2024-02-01"
    assert body["rows"][0]["cumulative_return"] == 0  # rebased to the range start
    assert all(r["drawdown"] <= 0 for r in body["rows"])


def test_unknown_market_is_404(local):
    assert local.get("/api/markets/NOPE/prices").status_code == 404


def test_public_mode_hides_non_redistributable_rows(local, public):
    local_rows = local.get("/api/markets/TSM/prices").json()
    public_rows = public.get("/api/markets/TSM/prices").json()
    assert local_rows["sources"] == ["tiingo", "yahoo_finance"]
    assert public_rows["sources"] == ["yahoo_finance"]
    assert len(public_rows["rows"]) == len(local_rows["rows"]) - 10


def test_correlation_matrix_is_square_with_unit_diagonal(local):
    body = local.get("/api/markets/correlation", params={"ids": "NVDA,MSFT,BTC"}).json()
    assert body["ids"] == ["NVDA", "MSFT", "BTC"]
    assert [body["matrix"][i][i] for i in range(3)] == [1.0, 1.0, 1.0]


def test_news_feed_filters_and_never_returns_article_text(local):
    body = local.get("/api/news", params={"q": "nvidia"}).json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["sentiment_label"] == "Bullish" and "description" not in item
    assert local.get("/api/news", params={"entity": "btc"}).json()["total"] == 1
    assert local.get("/api/news", params={"label": "Neutral"}).json()["total"] == 1
    assert local.get("/api/news", params={"from": "2024-01-03", "to": "2024-01-31"}).json()["total"] == 1
    assert local.get("/api/news", params={"page_size": 500}).status_code == 422


def test_sentiment_summary_label_filter_changes_counts(local):
    all_rows = local.get("/api/sentiment/summary").json()
    assert all_rows["model"] == "vader" and all_rows["n_scored"] == 3
    only_bullish = local.get("/api/sentiment/summary", params={"labels": "Bullish"}).json()
    assert only_bullish["n_scored"] == 1
    assert local.get("/api/sentiment/summary", params={"model": "bogus"}).status_code == 404


def test_model_report_nan_is_serialised_as_null(local):
    body = local.get("/api/models/report").json()
    assert body["models"]["xgboost"]["validation_metrics"]["roc_auc"] is None


def test_explainability_strips_transformer_prefixes(local):
    body = local.get("/api/models/explainability").json()
    assert body["importance"]["xgboost"] == [{"feature": "rsi_14d", "importance": 0.2}]


def test_events_include_caar_series(local):
    body = local.get("/api/events").json()
    assert [r["day"] for r in body["caar"]] == [-1, 0, 1]
    assert body["benchmark"] == "SPX"


def test_predictions_404_without_models(local):
    assert local.get("/api/predictions/latest").status_code == 404


def test_figures_are_whitelisted(local):
    assert local.get("/api/figures/13_roc_curves.png").status_code == 200
    assert local.get("/api/figures/secret.txt").status_code == 404
    assert local.get("/api/figures/..%2Fsecret.txt").status_code == 404


def test_pipeline_rejects_non_local_callers(local):
    # TestClient's client host is "testclient", not a loopback address
    assert local.get("/api/pipeline/jobs").status_code == 403
    assert local.post("/api/pipeline/run/features").status_code == 403


def test_pipeline_whitelist_for_local_callers(local):
    local.app.state.local_hosts.add("testclient")
    jobs = local.get("/api/pipeline/jobs").json()
    assert "features" in {j["name"] for j in jobs["available"]}
    assert local.post("/api/pipeline/run/rm_rf").status_code == 404
    assert local.post("/api/pipeline/run/features", json={"max_requests": 5}).status_code == 422


def test_public_mode_has_no_pipeline_or_docs(public):
    assert public.get("/api/meta").json()["pipeline_enabled"] is False
    assert public.post("/api/pipeline/run/features").status_code in (404, 405)
    assert public.get("/api/pipeline/jobs").status_code == 404
    assert public.get("/api/docs").status_code == 404


def test_spa_fallback_serves_index_but_not_api(data_dir):
    dist = data_dir / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>app</html>")
    client = TestClient(create_app("public", web_dist=dist))
    assert client.get("/stocks/NVDA").text == "<html>app</html>"
    assert client.get("/api/unknown").status_code == 404
    (data_dir / "secret.txt").write_text("nope")  # outside dist
    for path in ["/..%2Fsecret.txt", "/%2E%2E/secret.txt", "/assets/..%2F..%2Fsecret.txt"]:
        assert "nope" not in client.get(path).text


# --- predict_latest --------------------------------------------------------------

def _synthetic_features():
    rng = np.random.default_rng(0)
    rows = []
    for mid in ["NVDA", "BTC"]:
        for d in DATES:
            row = {c: rng.normal() for c in ALL_FEATURES if c != "market_id"}
            row.update(market_id=mid, date=d, close=100.0)
            rows.append(row)
    df = pd.DataFrame(rows)
    # the newest NVDA row lacks a dense feature, so the one before it is the latest usable
    df.loc[(df.market_id == "NVDA") & (df.date == DATES[-1]), "rsi_14d"] = np.nan
    return df


def test_latest_feature_rows_takes_newest_complete_row_per_asset():
    rows = latest_feature_rows(_synthetic_features(), market_ids=("NVDA", "BTC"))
    latest = dict(zip(rows.market_id, rows.date))
    assert latest == {"BTC": DATES[-1], "NVDA": DATES[-2]}
    assert not rows[MARKET_FEATURES + CROSS_SECTIONAL_FEATURES].isna().any().any()


def test_predict_latest_scores_each_saved_model(tmp_path):
    features = _synthetic_features()
    numeric, categorical = get_feature_columns()
    train = impute_sparse_features(features.dropna(subset=MARKET_FEATURES + CROSS_SECTIONAL_FEATURES))
    y = (train["return_1d"] > 0).astype(int)
    model = build_models()["logistic_regression"].fit(train[numeric + categorical], y)
    joblib.dump(model, tmp_path / "logistic_regression_h5d.joblib")

    result = predict_latest(features=features, model_dir=tmp_path, report_path=tmp_path / "missing.json")
    probs = result["models"]["logistic_regression"]["probabilities"]
    assert set(probs) == {"NVDA", "BTC"}
    assert all(0 <= p <= 1 for p in probs.values())
    assert {a["market_id"]: a["as_of"] for a in result["assets"]}["NVDA"] == str(DATES[-2].date())
