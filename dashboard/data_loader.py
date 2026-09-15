"""Cached loaders for the dashboard. Every function here reads already-
materialized artifacts from data/raw, data/processed, or outputs/ — nothing
in the dashboard fetches live data or trains a model on page load, per the
target spec's explicit instruction for Stage 14.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR, REFERENCE_DIR


@st.cache_data
def load_companies() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "companies.csv")


@st.cache_data
def load_company_ai_categories() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "company_ai_categories.csv")


@st.cache_data
def load_crypto_assets() -> pd.DataFrame:
    return pd.read_csv(REFERENCE_DIR / "crypto_assets.csv")


@st.cache_data
def load_events() -> pd.DataFrame:
    path = REFERENCE_DIR / "events.csv"
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


@st.cache_data
def list_ingested_market_ids() -> list[str]:
    market_dir = RAW_DIR / "market_prices"
    if not market_dir.exists():
        return []
    return sorted(p.stem for p in market_dir.glob("*.parquet"))


@st.cache_data
def load_market_prices(market_id: str) -> pd.DataFrame | None:
    path = RAW_DIR / "market_prices" / f"{market_id}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)


@st.cache_data
def load_all_market_prices() -> dict[str, pd.DataFrame]:
    return {mid: load_market_prices(mid) for mid in list_ingested_market_ids()}


@st.cache_data
def load_news() -> pd.DataFrame | None:
    path = RAW_DIR / "news" / "news.parquet"
    return pd.read_parquet(path) if path.exists() else None


@st.cache_data
def load_sentiment() -> pd.DataFrame | None:
    path = RAW_DIR / "sentiment" / "fact_sentiment.parquet"
    return pd.read_parquet(path) if path.exists() else None


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_model_report(horizon: int = 5) -> dict | None:
    return _load_json(PROCESSED_DIR / f"model_report_h{horizon}d.json")


@st.cache_data
def load_explainability_report(horizon: int = 5) -> dict | None:
    return _load_json(PROCESSED_DIR / f"explainability_report_h{horizon}d.json")


@st.cache_data
def load_indices_report() -> dict | None:
    return _load_json(PROCESSED_DIR / "indices_report.json")


@st.cache_data
def load_event_study_report() -> dict | None:
    return _load_json(PROCESSED_DIR / "event_study_report.json")


@st.cache_data
def load_feature_agreement(horizon: int = 5) -> pd.DataFrame | None:
    path = PROCESSED_DIR / f"feature_agreement_h{horizon}d.csv"
    return pd.read_csv(path) if path.exists() else None


def figure_path(name: str) -> Path:
    return OUTPUTS_DIR / "figures" / name
