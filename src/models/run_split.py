"""Stage 8 orchestrator: merges Stage 6 features with Stage 7 targets, applies
the chronological split (with embargo) per horizon, validates, and stores the
resulting ML-ready dataset. Run as: python -m src.models.run_split
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from src.config import PROCESSED_DIR
from src.ingestion.store import round_trip_matches
from src.ingestion.validate import ValidationResult
from src.models.split import DEFAULT_TRAIN_END, DEFAULT_VAL_END, add_split_labels

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

HORIZONS = (1, 5, 10)


def _validate_split(df: pd.DataFrame) -> ValidationResult:
    issues: list[str] = []
    for h in HORIZONS:
        col = f"split_{h}d"
        if col not in df.columns:
            issues.append(f"missing {col}")
            continue
        bad = ~df[col].isin(["train", "validation", "test", "excluded_embargo", "excluded_no_target"])
        if bad.any():
            issues.append(f"{col}: {bad.sum()} row(s) with an unrecognized split label")

        # chronological ordering: every assigned train date <= every assigned validation date
        # <= every assigned test date, per asset (this is the actual proof there's no shuffling).
        for market_id, group in df.groupby("market_id"):
            train_dates = group.loc[group[col] == "train", "date"]
            val_dates = group.loc[group[col] == "validation", "date"]
            test_dates = group.loc[group[col] == "test", "date"]
            if len(train_dates) and len(val_dates) and train_dates.max() >= val_dates.min():
                issues.append(f"{col}/{market_id}: train dates overlap into validation")
            if len(val_dates) and len(test_dates) and val_dates.max() >= test_dates.min():
                issues.append(f"{col}/{market_id}: validation dates overlap into test")

    return ValidationResult("split_dataset", len(issues) == 0, issues, len(df))


def main() -> None:
    features_path = PROCESSED_DIR / "features" / "features.parquet"
    targets_path = PROCESSED_DIR / "targets" / "target_table.parquet"
    if not features_path.exists() or not targets_path.exists():
        raise FileNotFoundError(
            "run src.features.run_features and src.features.run_target first"
        )

    features = pd.read_parquet(features_path)
    targets = pd.read_parquet(targets_path)

    merged = features.merge(targets, on=["market_id", "date"], how="inner", validate="one_to_one")
    if len(merged) != len(features):
        raise ValueError(
            f"feature/target merge dropped rows: features={len(features)} merged={len(merged)} "
            "— features and targets are no longer aligned 1:1 per (market_id, date)"
        )

    merged = add_split_labels(merged, HORIZONS, DEFAULT_TRAIN_END, DEFAULT_VAL_END)

    validation = _validate_split(merged)
    if not validation.passed:
        logger.error("validation failed: %s", validation.issues)
        raise ValueError(f"split validation failed: {validation.issues}")

    out_path = PROCESSED_DIR / "ml_dataset" / "ml_dataset.parquet"
    matches, rt_issues = round_trip_matches(merged, out_path)
    if not matches:
        raise ValueError(f"round-trip mismatch: {rt_issues}")

    report = {"train_end": DEFAULT_TRAIN_END, "val_end": DEFAULT_VAL_END, "by_horizon": {}}
    for h in HORIZONS:
        col = f"split_{h}d"
        counts = merged[col].value_counts().to_dict()
        report["by_horizon"][f"{h}d"] = counts
    with open(PROCESSED_DIR / "split_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)

    logger.info("Stage 8 split complete: %d rows, %d assets", len(merged), merged["market_id"].nunique())
    for h in HORIZONS:
        logger.info("horizon=%dd split counts: %s", h, report["by_horizon"][f"{h}d"])


if __name__ == "__main__":
    main()
