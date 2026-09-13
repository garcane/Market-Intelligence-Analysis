"""Stage 5 orchestrator: loads Stage 3/4 outputs, computes descriptive market
and sentiment statistics, generates figures, and writes EDA_SUMMARY.md.
Run as: python -m src.analytics.run_eda
"""
from __future__ import annotations

import json
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.analytics.market_stats import compute_market_stats, summary_stats
from src.analytics.relationships import (
    merge_sentiment_and_market,
    news_volume_volatility_correlation,
    sentiment_return_correlation,
)
from src.analytics.sentiment_stats import daily_sentiment, label_distribution, sentiment_by_entity
from src.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

FIGURES_DIR = OUTPUTS_DIR / "figures"
REPORTS_DIR = OUTPUTS_DIR / "reports"


def load_all_market_data() -> dict[str, pd.DataFrame]:
    market_dir = RAW_DIR / "market_prices"
    data = {}
    for path in sorted(market_dir.glob("*.parquet")):
        market_id = path.stem
        data[market_id] = pd.read_parquet(path)
    return data


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    market_data = load_all_market_data()
    if not market_data:
        raise FileNotFoundError("no market data found — run src.ingestion.run_ingestion first")
    logger.info("loaded market data for: %s", list(market_data.keys()))

    market_stats = {mid: compute_market_stats(df) for mid, df in market_data.items()}
    summaries = {mid: summary_stats(df) for mid, df in market_stats.items()}

    # --- Figure 1: price charts (small multiples) ---
    fig, axes = plt.subplots(len(market_stats), 1, figsize=(12, 3 * len(market_stats)), sharex=False)
    axes = axes if hasattr(axes, "__iter__") else [axes]
    for ax, (mid, df) in zip(axes, market_stats.items()):
        ax.plot(df["date"], df["close"])
        ax.set_title(f"{mid} — Close Price")
        ax.set_ylabel("Price (USD)")
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "01_price_charts.png", dpi=110)
    plt.close(fig)

    # --- Figure 2: cumulative returns, all assets on one chart ---
    fig, ax = plt.subplots(figsize=(12, 6))
    for mid, df in market_stats.items():
        ax.plot(df["date"], df["cumulative_return"], label=mid)
    ax.set_title("Cumulative Return by Asset")
    ax.set_ylabel("Cumulative Return")
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "02_cumulative_returns.png", dpi=110)
    plt.close(fig)

    # --- Figure 3: drawdown ---
    fig, ax = plt.subplots(figsize=(12, 6))
    for mid, df in market_stats.items():
        ax.plot(df["date"], df["drawdown"], label=mid)
    ax.set_title("Drawdown by Asset")
    ax.set_ylabel("Drawdown")
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "03_drawdown.png", dpi=110)
    plt.close(fig)

    # --- Figure 4: rolling volatility ---
    fig, ax = plt.subplots(figsize=(12, 6))
    for mid, df in market_stats.items():
        ax.plot(df["date"], df["rolling_vol_30d"], label=mid)
    ax.set_title("30-Day Rolling Volatility (log-return std)")
    ax.set_ylabel("Volatility")
    ax.legend()
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "04_rolling_volatility.png", dpi=110)
    plt.close(fig)

    # --- Figure 5: return correlation matrix across assets ---
    returns_wide = pd.DataFrame({mid: df.set_index("date")["log_return_1d"] for mid, df in market_stats.items()})
    corr_matrix = returns_wide.corr()
    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(corr_matrix, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(corr_matrix)), corr_matrix.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr_matrix)), corr_matrix.index)
    for i in range(len(corr_matrix)):
        for j in range(len(corr_matrix)):
            ax.text(j, i, f"{corr_matrix.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    ax.set_title("Daily Log-Return Correlation Matrix")
    plt.colorbar(im)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "05_return_correlation_matrix.png", dpi=110)
    plt.close(fig)

    # --- Sentiment data ---
    sentiment_path = RAW_DIR / "sentiment" / "fact_sentiment.parquet"
    news_path = RAW_DIR / "news" / "news.parquet"
    relationship_results = {}
    label_dist = None
    entity_sentiment = None

    if sentiment_path.exists() and news_path.exists():
        sentiment_df = pd.read_parquet(sentiment_path)
        news_df = pd.read_parquet(news_path)

        label_dist = label_distribution(sentiment_df, "vader")
        entity_sentiment = sentiment_by_entity(sentiment_df, news_df, "matched_company_id", "vader")

        daily_sent = daily_sentiment(sentiment_df, news_df, "vader")

        # --- Figure 6: sentiment distribution ---
        fig, ax = plt.subplots(figsize=(10, 5))
        for model in ["vader", "textblob"]:
            scores = sentiment_df[sentiment_df["sentiment_model"] == model]["sentiment_score"]
            ax.hist(scores, bins=30, alpha=0.5, label=model)
        ax.set_title("Sentiment Score Distribution: VADER vs TextBlob")
        ax.set_xlabel("Sentiment Score")
        ax.legend()
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "06_sentiment_distribution.png", dpi=110)
        plt.close(fig)

        # --- Figure 7: sentiment by company (top 10 by article count) ---
        top_entities = entity_sentiment.head(10)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.barh(top_entities["matched_company_id"], top_entities["mean_sentiment"])
        ax.set_title("Mean VADER Sentiment by Company (top 10 by article count)")
        ax.set_xlabel("Mean Sentiment Score")
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "07_sentiment_by_company.png", dpi=110)
        plt.close(fig)

        # --- Relationships: microsoft news sentiment vs MSFT returns (if both exist) ---
        entity_market_map = {"microsoft": "MSFT", "alphabet": "GOOGL", "amazon": "AMZN",
                              "apple": "AAPL", "meta": "META"}
        for entity_id, market_id in entity_market_map.items():
            if market_id not in market_stats:
                continue
            entity_daily = daily_sentiment(
                sentiment_df,
                news_df[news_df["matched_company_id"] == entity_id],
                "vader",
            )
            if entity_daily.empty:
                continue
            merged = merge_sentiment_and_market(entity_daily, market_stats[market_id])
            relationship_results[f"{entity_id}_sentiment_vs_{market_id}_return"] = {
                **sentiment_return_correlation(merged),
                "news_volume_vs_volatility": news_volume_volatility_correlation(merged),
            }
    else:
        logger.warning("no sentiment data found — skipping sentiment EDA (run src.sentiment.run_sentiment first)")

    # --- Write summary report ---
    lines = ["# EDA_SUMMARY.md — Stage 5 Exploratory Data Analysis\n"]
    lines.append("Auto-generated by `src/analytics/run_eda.py`. All figures in `outputs/figures/`.\n")
    lines.append("## Market Summary Statistics\n")
    lines.append("| Asset | Days | Start | End | Mean Daily Return | Ann. Volatility | Max Drawdown | Total Return |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for mid, s in summaries.items():
        lines.append(f"| {mid} | {s['n_days']} | {s['start_date']} | {s['end_date']} | "
                      f"{s['mean_daily_return']:.4%} | {s['annualized_volatility']:.2%} | "
                      f"{s['max_drawdown']:.2%} | {s['total_return']:.2%} |")

    if label_dist is not None:
        lines.append("\n## Sentiment Label Distribution (VADER)\n")
        for label, count in label_dist.items():
            lines.append(f"- {label}: {count}")

    if entity_sentiment is not None:
        lines.append("\n## Sentiment by Company (top 10 by article count)\n")
        lines.append("| Company | Articles | Mean Sentiment | Std Sentiment |")
        lines.append("|---|---|---|---|")
        for _, row in entity_sentiment.head(10).iterrows():
            lines.append(f"| {row['matched_company_id']} | {row['n_articles']} | "
                          f"{row['mean_sentiment']:.3f} | {row['std_sentiment']:.3f} |")

    if relationship_results:
        lines.append("\n## Sentiment <-> Return Relationships (same-day correlation)\n")
        lines.append("**Correlation is not evidence of causation** — these are small, same-day, "
                      "exploratory correlations on a short backfilled sample and must not be read as "
                      "predictive or causal relationships.\n")
        any_nonzero_n = any(r["n_obs"] > 0 for r in relationship_results.values())
        for key, result in relationship_results.items():
            if result["n_obs"] == 0:
                lines.append(f"- `{key}`: n=0 — no overlapping dates (see note below)")
                continue
            too_small = result["n_obs"] < 10
            flag = "  **[n<10: NOT statistically interpretable — ignore this correlation]**" if too_small else ""
            lines.append(f"- `{key}`: n={result['n_obs']}, "
                          f"sentiment-return correlation={result.get('correlation', float('nan')):.3f}, "
                          f"news_volume-volatility correlation="
                          f"{result['news_volume_vs_volatility'].get('correlation', float('nan')):.3f}{flag}")
        if not any_nonzero_n:
            lines.append("\n**Known limitation:** every pairing above has n=0 overlapping observations. "
                          "Google News RSS (the key-free news source used in Stage 3/4) only returns "
                          "*currently available* headlines — it has no historical archive endpoint — "
                          "while `fact_market_prices` here is a 2023-06 to 2024-06 backfill. The two date "
                          "ranges genuinely do not overlap given today's date, so this correlation cannot "
                          "be computed from the current data sources. Fixing this requires either a paid "
                          "historical news API (set `NEWS_API_KEY` — see `.env.example`) or restricting "
                          "market backfills to the news source's actual coverage window; it is not a bug "
                          "in the relationship-analysis code itself, which is otherwise unit-tested "
                          "(`tests/test_analytics.py::TestRelationships`).")
    else:
        lines.append("\n## Sentiment <-> Return Relationships\n")
        lines.append("No entity in the news data both matched a company and had ingested price data "
                      "for its ticker in the current sample.")

    lines.append("\n## Return Correlation Matrix\n")
    lines.append("See `outputs/figures/05_return_correlation_matrix.png`.\n")

    lines.append("\n## Caveats\n")
    lines.append("- Sample sizes are small (single-year backfills, a handful of assets/companies) — "
                  "figures here are illustrative of the pipeline, not statistically powered conclusions.")
    lines.append("- All sentiment-return correlations are same-day and descriptive only; no lag "
                  "structure or causal identification strategy has been applied (that is Stage 6+ work).")

    with open(REPORTS_DIR / "EDA_SUMMARY.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    with open(PROCESSED_DIR / "eda_report.json", "w", encoding="utf-8") as f:
        json.dump({"market_summaries": summaries, "relationships": relationship_results},
                   f, indent=2, default=str)

    logger.info("Stage 5 EDA complete. Figures in %s, summary in %s",
                FIGURES_DIR, REPORTS_DIR / "EDA_SUMMARY.md")


if __name__ == "__main__":
    main()
