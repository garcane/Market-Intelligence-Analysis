"""Orchestrates the ablation study (target spec §20). Run as:
python -m src.models.run_ablation
"""
from __future__ import annotations

import json
import logging

import pandas as pd

from src.config import PROCESSED_DIR
from src.features.target import PRIMARY_HORIZON
from src.models.ablation import run_ablation

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    ml_dataset = pd.read_parquet(PROCESSED_DIR / "ml_dataset" / "ml_dataset.parquet")
    results = run_ablation(ml_dataset, horizon=PRIMARY_HORIZON)

    for exp_name, metrics in results.items():
        logger.info("%s (%d features): PR-AUC=%.3f ROC-AUC=%.3f F1=%.3f",
                     exp_name, metrics["n_features"], metrics["pr_auc"], metrics["roc_auc"], metrics["f1"])

    with open(PROCESSED_DIR / "ablation_report.json", "w", encoding="utf-8") as f:
        json.dump({"horizon": PRIMARY_HORIZON, "results": results}, f, indent=2, default=str)
    logger.info("Ablation report written to %s", PROCESSED_DIR / "ablation_report.json")


if __name__ == "__main__":
    main()
