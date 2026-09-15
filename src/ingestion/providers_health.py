"""Persist API/provider health telemetry for inspection and dashboards."""
from __future__ import annotations

import json
from pathlib import Path

from src.config import PROCESSED_DIR


def write_health_report(report: dict, path: Path | None = None) -> Path:
    destination = path or (PROCESSED_DIR / "provider_health.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    return destination
