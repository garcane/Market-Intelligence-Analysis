"""Stage 13 (sentiment visualizations): sentiment over time (across all
matched entities) and sentiment by sector — the two Stage 13 chart categories
Stage 5's EDA didn't already cover (it did distribution and by-company).
Run as: python -m src.analytics.run_sentiment_viz
"""
from __future__ import annotations

import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.analytics.sentiment_stats import daily_sentiment
from src.config import OUTPUTS_DIR, RAW_DIR, REFERENCE_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

FIGURES_DIR = OUTPUTS_DIR / "figures"


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    sentiment_path = RAW_DIR / "sentiment" / "fact_sentiment.parquet"
    news_path = RAW_DIR / "news" / "news.parquet"
    if not sentiment_path.exists() or not news_path.exists():
        raise FileNotFoundError("run src.sentiment.run_sentiment first")

    sentiment_df = pd.read_parquet(sentiment_path)
    news_df = pd.read_parquet(news_path)

    # --- sentiment over time, across all matched news (not just one entity) ---
    daily = daily_sentiment(sentiment_df, news_df, "vader")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
    ax1.plot(daily["date"], daily["mean_sentiment"], marker="o", markersize=3)
    ax1.axhline(0, color="gray", linewidth=0.5)
    ax1.set_title("Mean VADER Sentiment Over Time (all matched entities)")
    ax1.set_ylabel("Mean sentiment")
    ax2.bar(daily["date"], daily["news_volume"])
    ax2.set_title("News Volume Over Time")
    ax2.set_ylabel("Article count")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "13_sentiment_over_time.png", dpi=110)
    plt.close(fig)
    logger.info("sentiment-over-time: %d days with matched news coverage", len(daily))

    # --- sentiment by sector (join matched_company_id -> theme segment) ---
    themes = pd.read_csv(REFERENCE_DIR / "themes.csv")
    categories = pd.DataFrame({"company_id": themes["entity_id"],
                               "ai_category": themes["theme"] + " / " + themes["segment"]})
    scored = sentiment_df[sentiment_df["sentiment_model"] == "vader"]
    merged = scored.merge(news_df[["news_id", "matched_company_id"]], on="news_id", how="left")
    merged = merged.merge(categories, left_on="matched_company_id", right_on="company_id", how="left")
    merged = merged[merged["ai_category"].notna()]

    by_sector = merged.groupby("ai_category")["sentiment_score"].agg(
        mean_sentiment="mean", n_articles="count").reset_index().sort_values("n_articles", ascending=False)

    if not by_sector.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.barh(by_sector["ai_category"], by_sector["mean_sentiment"])
        ax.axvline(0, color="gray", linewidth=0.5)
        ax.set_title("Mean VADER Sentiment by Theme Segment")
        ax.set_xlabel("Mean sentiment score")
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "13_sentiment_by_sector.png", dpi=110)
        plt.close(fig)
        logger.info("sentiment-by-sector: %d categories with matched coverage:\n%s",
                    len(by_sector), by_sector.to_string(index=False))
    else:
        logger.warning("no news rows matched to an ai_category — skipping sentiment-by-sector figure")


if __name__ == "__main__":
    main()
