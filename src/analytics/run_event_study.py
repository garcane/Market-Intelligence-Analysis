"""Stage 11 orchestrator: computes event-window abnormal returns for the
curated event catalog (data/reference/events.csv), aggregates CAAR, and
produces figures. Run as: python -m src.analytics.run_event_study
"""
from __future__ import annotations

import json
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.analytics.event_study import abnormal_return_window, average_car_across_events, event_window_returns
from src.analytics.market_stats import add_returns
from src.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR, REFERENCE_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

FIGURES_DIR = OUTPUTS_DIR / "figures"
BENCHMARK_ID = "SPX"
WINDOW = 5


def load_returns(market_id: str) -> pd.DataFrame | None:
    path = RAW_DIR / "market_prices" / f"{market_id}.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)[["date", "close"]]
    return add_returns(df)


def main() -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    events = pd.read_csv(REFERENCE_DIR / "events.csv")
    benchmark_df = load_returns(BENCHMARK_ID)
    if benchmark_df is None:
        raise FileNotFoundError(f"benchmark {BENCHMARK_ID} not ingested — run src.analytics.fetch_benchmarks first")

    report = {"benchmark": BENCHMARK_ID, "window": WINDOW, "events": []}
    car_windows = {}
    raw_windows = {}

    for _, row in events.iterrows():
        event_id, market_id, event_date = row["event_id"], row["primary_market_id"], row["event_date"]
        asset_df = load_returns(market_id)
        entry = {"event_id": event_id, "market_id": market_id, "event_date": event_date,
                 "title": row["title"]}
        if asset_df is None:
            entry["status"] = "SKIPPED_NOT_INGESTED"
            report["events"].append(entry)
            continue

        raw_window = event_window_returns(asset_df["return_1d"], asset_df["date"], event_date, WINDOW)
        ar_window = abnormal_return_window(
            asset_df["return_1d"], asset_df["date"],
            benchmark_df["return_1d"], benchmark_df["date"], event_date, WINDOW,
        )
        if raw_window is None or ar_window is None:
            entry["status"] = "SKIPPED_OUT_OF_RANGE"
            report["events"].append(entry)
            continue

        entry["status"] = "OK"
        entry["t0_raw_return"] = float(raw_window.loc[0])
        entry["t0_abnormal_return"] = float(ar_window.loc[0])
        entry["cumulative_abnormal_return_full_window"] = float(ar_window.sum())
        report["events"].append(entry)
        car_windows[event_id] = ar_window
        raw_windows[event_id] = raw_window

        # --- per-event figure ---
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.bar(ar_window.index, ar_window.values, color=["#d62728" if x < 0 else "#2ca02c" for x in ar_window.values])
        ax.axvline(0, color="black", linewidth=1, linestyle="--")
        ax.set_title(f"{market_id} abnormal return (vs {BENCHMARK_ID}) around {row['title']}\n{event_date}")
        ax.set_xlabel("Trading days relative to event")
        ax.set_ylabel("Abnormal return")
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / f"11_event_{event_id}.png", dpi=110)
        plt.close(fig)

        logger.info("%s (%s, %s): T0 raw=%.4f T0 abnormal=%.4f", event_id, market_id, event_date,
                    entry["t0_raw_return"], entry["t0_abnormal_return"])

    # --- CAAR across all resolvable events ---
    if car_windows:
        caar_table = average_car_across_events(car_windows)
        caar_table.to_csv(PROCESSED_DIR / "event_study_caar.csv")

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(caar_table.index, caar_table["CAAR"], marker="o")
        ax.axvline(0, color="black", linewidth=1, linestyle="--")
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.set_title(f"Cumulative Average Abnormal Return (CAAR) across {len(car_windows)} events, "
                     f"vs {BENCHMARK_ID}")
        ax.set_xlabel("Trading days relative to event")
        ax.set_ylabel("CAAR")
        plt.tight_layout()
        plt.savefig(FIGURES_DIR / "11_caar_all_events.png", dpi=110)
        plt.close(fig)

        report["caar_summary"] = caar_table.to_dict(orient="index")

    with open(PROCESSED_DIR / "event_study_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    n_ok = sum(1 for e in report["events"] if e["status"] == "OK")
    logger.info("Stage 11 complete: %d/%d events resolved", n_ok, len(report["events"]))


if __name__ == "__main__":
    main()
