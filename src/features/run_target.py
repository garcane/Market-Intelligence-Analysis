"""Stage 7 orchestrator: builds the classification target table, runs the
threshold/volatility analysis that justifies the chosen threshold, validates,
and stores everything. Run as: python -m src.features.run_target
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from src.config import PROCESSED_DIR, RAW_DIR
from src.features.target import DEFAULT_THRESHOLD, HORIZONS, build_target_table
from src.features.target_analysis import class_balance_grid, realized_volatility_by_asset
from src.ingestion.store import round_trip_matches
from src.ingestion.validate import ValidationResult

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def load_market_prices() -> dict[str, pd.DataFrame]:
    market_dir = RAW_DIR / "market_prices"
    return {path.stem: pd.read_parquet(path) for path in sorted(market_dir.glob("*.parquet"))}


def _validate_target_table(df: pd.DataFrame) -> ValidationResult:
    issues: list[str] = []
    dupes = df.duplicated(subset=["market_id", "date"]).sum()
    if dupes:
        issues.append(f"{dupes} duplicate (market_id, date) row(s)")

    for h in HORIZONS:
        col = f"target_{h}d"
        non_null = df[col].dropna()
        bad_values = ~non_null.isin([0.0, 1.0])
        if bad_values.any():
            issues.append(f"{col}: {bad_values.sum()} non-binary value(s)")

        # the last h rows of every asset must have a NaN target (no known future price)
        for market_id, group in df.groupby("market_id"):
            group = group.sort_values("date")
            last_h = group[col].iloc[-h:]
            if last_h.notna().any():
                issues.append(f"{col} for market_id={market_id}: expected the last {h} row(s) "
                               f"to be NaN (no future price available), found a non-null value")

    return ValidationResult("target_table", len(issues) == 0, issues, len(df))


def main() -> None:
    market_prices = load_market_prices()
    if not market_prices:
        raise FileNotFoundError("no market data found — run src.ingestion.run_ingestion first")

    target_table = build_target_table(market_prices, HORIZONS, DEFAULT_THRESHOLD)
    validation = _validate_target_table(target_table)
    if not validation.passed:
        logger.error("validation failed: %s", validation.issues)
        raise ValueError(f"target table validation failed: {validation.issues}")

    out_path = PROCESSED_DIR / "targets" / "target_table.parquet"
    matches, rt_issues = round_trip_matches(target_table, out_path)
    if not matches:
        raise ValueError(f"round-trip mismatch: {rt_issues}")

    balance = class_balance_grid(market_prices)
    vol = realized_volatility_by_asset(market_prices)

    balance.to_csv(PROCESSED_DIR / "target_class_balance.csv", index=False)
    vol.to_csv(PROCESSED_DIR / "target_realized_volatility.csv", index=False)

    primary = balance[(balance["horizon"] == 5) & (balance["threshold"] == DEFAULT_THRESHOLD)]
    report = {
        "n_rows": len(target_table),
        "n_assets": int(target_table["market_id"].nunique()),
        "horizons": list(HORIZONS),
        "default_threshold": DEFAULT_THRESHOLD,
        "primary_horizon_5d_threshold_0.02_positive_rate_by_asset":
            primary.set_index("market_id")["positive_rate"].round(4).to_dict(),
        "realized_volatility_by_asset": vol.round(4).to_dict(orient="records"),
    }
    with open(PROCESSED_DIR / "target_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("Stage 7 target table built: %d rows, %d assets", len(target_table),
                target_table["market_id"].nunique())
    logger.info("Primary (5d, 2%% threshold) positive rate by asset: %s",
                report["primary_horizon_5d_threshold_0.02_positive_rate_by_asset"])


if __name__ == "__main__":
    main()
