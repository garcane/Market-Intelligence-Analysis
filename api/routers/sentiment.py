"""Sentiment summaries and the searchable news feed."""
from __future__ import annotations

from datetime import date

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from api import data
from src.analytics.sentiment_stats import daily_sentiment, label_distribution, sentiment_by_entity

router = APIRouter(prefix="/api", tags=["sentiment"])

# Headline, link and metadata only: article text stays with the publisher.
NEWS_FIELDS = ["news_id", "timestamp", "title", "source", "source_id", "url", "entity", "asset_type",
               "matched_company_id", "matched_asset_id"]
MAX_PAGE_SIZE = 100


def _models(sent: pd.DataFrame | None) -> list[str]:
    return sorted(sent["sentiment_model"].dropna().unique().tolist()) if sent is not None else []


def _pick_model(sent: pd.DataFrame | None, model: str | None) -> str | None:
    models = _models(sent)
    if model and model not in models:
        raise HTTPException(404, f"unknown sentiment model {model!r}; available: {models}")
    return model or ("vader" if "vader" in models else (models[0] if models else None))


@router.get("/sentiment/summary")
def sentiment_summary(model: str | None = None,
                      labels: str | None = Query(None, description="comma-separated labels to include")) -> dict:
    sent, news = data.sentiment(), data.news()
    coverage = data.processed_json("news_coverage.json")
    chosen = _pick_model(sent, model)
    if sent is None or news is None or chosen is None:
        return {"models": [], "model": None, "labels": [], "distribution": [], "by_entity": [],
                "daily": [], "coverage": coverage}
    all_labels = sorted(sent["sentiment_label"].dropna().unique().tolist())
    if labels:
        sent = sent[sent["sentiment_label"].isin(labels.split(","))]
    dist = label_distribution(sent, chosen)
    daily = daily_sentiment(sent, news, chosen)
    daily["date"] = pd.to_datetime(daily["date"])
    return data.clean({
        "models": _models(data.sentiment()),
        "model": chosen,
        "labels": all_labels,
        "n_scored": int((sent["sentiment_model"] == chosen).sum()),
        "distribution": [{"label": k, "count": int(v)} for k, v in dist.items()],
        "by_entity": data.records(sentiment_by_entity(sent, news, sentiment_model=chosen), date_cols=()),
        "daily": data.records(daily),
        "coverage": coverage,
    })


@router.get("/news")
def news_feed(q: str | None = None, entity: str | None = None, source: str | None = None,
              label: str | None = None, model: str | None = None,
              start: date | None = Query(None, alias="from"), end: date | None = Query(None, alias="to"),
              page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=MAX_PAGE_SIZE)) -> dict:
    news, sent = data.news(), data.sentiment()
    if news is None:
        return {"total": 0, "page": page, "page_size": page_size, "items": [], "facets": {}}
    df = news[NEWS_FIELDS]
    chosen = _pick_model(sent, model)
    if chosen is not None:
        scores = sent[sent["sentiment_model"] == chosen][["news_id", "sentiment_score", "sentiment_label"]]
        df = df.merge(scores, on="news_id", how="left")
    else:
        df = df.assign(sentiment_score=None, sentiment_label=None)

    facets = {
        "sources": sorted(df["source"].dropna().unique().tolist()),
        "entities": sorted(set(df["entity"].dropna()) | set(df["matched_company_id"].dropna())
                           | set(df["matched_asset_id"].dropna())),
        "labels": sorted(df["sentiment_label"].dropna().unique().tolist()),
    }
    if q:
        df = df[df["title"].str.contains(q, case=False, na=False, regex=False)]
    if entity:
        df = df[(df["entity"] == entity) | (df["matched_company_id"] == entity) | (df["matched_asset_id"] == entity)]
    if source:
        df = df[df["source"] == source]
    if label:
        df = df[df["sentiment_label"] == label]
    if start:
        df = df[df["timestamp"] >= pd.Timestamp(start)]
    if end:
        df = df[df["timestamp"] < pd.Timestamp(end) + pd.Timedelta(days=1)]

    df = df.sort_values("timestamp", ascending=False)
    page_df = df.iloc[(page - 1) * page_size: page * page_size]
    return data.clean({"total": len(df), "page": page, "page_size": page_size, "model": chosen,
                       "items": data.records(page_df, date_cols=()), "facets": facets})
