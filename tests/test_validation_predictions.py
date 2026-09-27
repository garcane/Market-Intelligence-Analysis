"""Validation-prediction export for the web app's model charts."""
import json

import numpy as np
import pytest

from src.models import validation_predictions as vp


def test_payload_shape_and_rounding():
    payload = vp.build_payload(5, np.array([0, 1, 1, 0]), {"m": np.array([0.1, 0.123456789, 0.9, 0.5])},
                               {"baseline_x": {"tn": 2, "fp": 0, "fn": 2, "tp": 0}})
    assert payload["n_validation"] == 4 and payload["base_rate"] == 0.5
    assert payload["y_true"] == [0, 1, 1, 0]
    assert payload["models"]["m"][1] == 0.123457
    assert payload["baselines"]["baseline_x"]["fn"] == 2
    json.dumps(payload)  # plain Python types only


def test_rejects_misaligned_probabilities():
    with pytest.raises(ValueError):
        vp.build_payload(5, np.array([0, 1]), {"m": np.array([0.1])}, {})


def test_exported_predictions_reproduce_the_model_report():
    """At threshold 0.5 the exported probabilities give exactly the report's
    confusion matrices. Runs against the local pipeline outputs; skipped on a
    fresh clone, where data/ is empty."""
    path, report_path = vp.output_path(5), vp.PROCESSED_DIR / "model_report_h5d.json"
    if not (path.exists() and report_path.exists()):
        pytest.skip("pipeline outputs not present")
    payload = json.loads(path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    y = np.array(payload["y_true"])
    for name, proba in payload["models"].items():
        pred = np.array(proba) >= 0.5
        counts = {"tn": int((~pred & (y == 0)).sum()), "fp": int((pred & (y == 0)).sum()),
                  "fn": int((~pred & (y == 1)).sum()), "tp": int((pred & (y == 1)).sum())}
        assert counts == report["models"][name]["validation_metrics"]["confusion_matrix"], name
    for name, counts in payload["baselines"].items():
        assert counts == report["models"][name]["validation_metrics"]["confusion_matrix"]
