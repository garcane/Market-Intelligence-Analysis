"""News ingestion via Google News RSS (key-free, structured XML — not HTML
scraping) with retries/timeouts, plus rule-based entity matching against the
Stage 1 company/crypto universe. Entity matching here is intentionally simple
substring matching; Stage 4 (NLP pipeline) is responsible for refining it.
"""
from __future__ import annotations

import hashlib
import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import pandas as pd
import requests

from src.ingestion.universe import load_companies, load_crypto_assets

logger = logging.getLogger(__name__)

RSS_URL = "https://news.google.com/rss/search"
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 20


class FetchError(Exception):
    pass


def _news_id(source: str, url: str, timestamp: datetime) -> str:
    key = f"{source}|{url}|{timestamp.isoformat()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def fetch_headlines(query: str, max_results: int = 30,
                     max_retries: int = MAX_RETRIES) -> pd.DataFrame:
    """Fetch recent headlines for `query` from Google News RSS."""
    params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(RSS_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS,
                                 headers={"User-Agent": "Mozilla/5.0 (AI-Market-Intelligence/1.0)"})
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = root.findall("./channel/item")[:max_results]

            rows = []
            for item in items:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub_date_raw = item.findtext("pubDate")
                source_el = item.find("source")
                source_name = source_el.text.strip() if source_el is not None and source_el.text else "google_news"
                if not title or not link:
                    continue
                try:
                    ts = parsedate_to_datetime(pub_date_raw) if pub_date_raw else datetime.now(timezone.utc)
                except (TypeError, ValueError):
                    ts = datetime.now(timezone.utc)
                rows.append({
                    "news_id": _news_id(source_name, link, ts),
                    "timestamp": ts.replace(tzinfo=None),
                    "source_id": source_name.lower().replace(" ", "_"),
                    "title": title,
                    "description": None,
                    "url": link,
                    "query": query,
                })
            return pd.DataFrame(rows, columns=[
                "news_id", "timestamp", "source_id", "title", "description", "url", "query",
            ])
        except Exception as exc:  # noqa: BLE001 - broad: network/XML errors of many types
            last_error = exc
            logger.warning("news fetch attempt %d/%d failed for query=%r: %s", attempt, max_retries, query, exc)
            if attempt < max_retries:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    raise FetchError(f"all {max_retries} attempts failed for query={query!r}: {last_error}")


def match_entities(news_df: pd.DataFrame) -> pd.DataFrame:
    """Adds matched_company_id / matched_asset_id / category via case-insensitive
    substring matching of company/asset names and tickers against the headline title.
    """
    companies = load_companies()[["company_id", "company_name", "ticker"]].copy()
    crypto = load_crypto_assets()[["asset_id", "asset_name", "symbol"]].copy()

    df = news_df.copy()
    df["matched_company_id"] = None
    df["matched_asset_id"] = None

    titles_lower = df["title"].str.lower()

    for _, row in companies.iterrows():
        needles = [row["company_name"].lower()]
        if isinstance(row["ticker"], str) and row["ticker"]:
            needles.append(row["ticker"].lower())
        mask = titles_lower.apply(lambda t: any(n in t for n in needles))
        df.loc[mask & df["matched_company_id"].isna(), "matched_company_id"] = row["company_id"]

    for _, row in crypto.iterrows():
        needles = [row["asset_name"].lower(), row["symbol"].lower()]
        mask = titles_lower.apply(lambda t: any(n in t for n in needles))
        df.loc[mask & df["matched_asset_id"].isna(), "matched_asset_id"] = row["asset_id"]

    df["category"] = "general"
    return df
