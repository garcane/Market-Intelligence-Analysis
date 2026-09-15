"""Stage 12 orchestrator: builds the thematic AI equity indices, compares
against benchmarks, and produces figures + INDICES.md-ready numbers.
Run as: python -m src.analytics.run_indices
"""
from __future__ import annotations

import json
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.analytics.indices import (
    BENCHMARK_IDS,
    INDEX_MEMBERS,
    beta,
    build_index_return,
    cumulative_return,
    index_summary,
    rolling_correlation,
)
from src.analytics.market_stats import add_returns
from src.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

FIGURES_DIR = OUTPUTS_DIR / "figures"


def load_all_returns() -> pd.DataFrame:
    market_dir = RAW_DIR / "market_prices"
    series = {}
    for path in sorted(market_dir.glob("*.parquet")):
        df = pd.read_parquet(path)[["date", "close"]]
        df = add_returns(df)
        series[path.stem] = df.set_index("date")["return_1d"]
    return pd.DataFrame(series)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    returns_wide = load_all_returns()
    logger.info("loaded returns for: %s", list(returns_wide.columns))

    index_returns = {}
    missing_members_report = {}
    for index_name, members in INDEX_MEMBERS.items():
        available = [m for m in members if m in returns_wide.columns]
        missing = [m for m in members if m not in returns_wide.columns]
        if missing:
            missing_members_report[index_name] = missing
        index_returns[index_name] = build_index_return(returns_wide, members)
        logger.info("%s: %d/%d constituents available (%s)", index_name, len(available), len(members), available)

    report = {"index_members": INDEX_MEMBERS, "missing_members": missing_members_report, "indices": {}}

    # --- Figure: cumulative return, indices + benchmarks ---
    fig, ax = plt.subplots(figsize=(12, 6))
    for name, returns in index_returns.items():
        ax.plot(returns.index, cumulative_return(returns), label=name, linewidth=2)
    for bench in BENCHMARK_IDS:
        if bench in returns_wide.columns:
            ax.plot(returns_wide.index, cumulative_return(returns_wide[bench]), label=bench,
                     linestyle="--", alpha=0.6)
    ax.set_title("AI Thematic Indices vs Benchmarks — Cumulative Return")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "12_indices_cumulative_return.png", dpi=110)
    plt.close(fig)

    # --- per-index stats + beta vs each benchmark ---
    for index_name, returns in index_returns.items():
        summary = index_summary(returns)
        betas = {}
        for bench in BENCHMARK_IDS:
            if bench in returns_wide.columns:
                betas[bench] = beta(returns, returns_wide[bench])
        report["indices"][index_name] = {**summary, "beta": betas}

    # --- benchmark stats too, for direct comparison ---
    for bench in BENCHMARK_IDS:
        if bench in returns_wide.columns:
            report["indices"][bench] = index_summary(returns_wide[bench])

    # --- Figure: rolling 30d correlation of each index vs SPX ---
    if "SPX" in returns_wide.columns:
        fig, ax = plt.subplots(figsize=(12, 6))
        for name, returns in index_returns.items():
            corr = rolling_correlation(returns, returns_wide["SPX"], window=30)
            ax.plot(corr.index, corr, label=f"{name} vs SPX")
        ax.set_title("30-Day Rolling Correlation vs S&P 500")
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "12_rolling_correlation_vs_spx.png", dpi=110)
        plt.close(fig)

    # --- Figure: correlation matrix, indices + benchmarks ---
    combined = pd.DataFrame(index_returns)
    for bench in BENCHMARK_IDS:
        if bench in returns_wide.columns:
            combined[bench] = returns_wide[bench]
    corr_matrix = combined.corr()
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(corr_matrix, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(corr_matrix)), corr_matrix.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(corr_matrix)), corr_matrix.index, fontsize=8)
    for i in range(len(corr_matrix)):
        for j in range(len(corr_matrix)):
            ax.text(j, i, f"{corr_matrix.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
    ax.set_title("Index/Benchmark Correlation Matrix")
    plt.colorbar(im)
    plt.tight_layout()
    plt.savefig(FIGURES_DIR / "12_index_correlation_matrix.png", dpi=110)
    plt.close(fig)

    with open(PROCESSED_DIR / "indices_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("Stage 12 complete. Report: %s", PROCESSED_DIR / "indices_report.json")


if __name__ == "__main__":
    main()
