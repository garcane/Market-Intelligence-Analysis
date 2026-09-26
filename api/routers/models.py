"""Model evaluation, explainability, latest predictions and saved figures."""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from api import data
from src.models.predict import FEATURES_PATH, MODEL_DIR, predict_latest

router = APIRouter(prefix="/api", tags=["models"])

FIGURE_NAME = re.compile(r"^[A-Za-z0-9_\-]+\.png$")
FEATURE_PREFIX = re.compile(r"^(numeric|categorical)__")


def _horizon_report(horizon: int) -> dict:
    report = data.processed_json(f"model_report_h{horizon}d.json")
    if report is None:
        raise HTTPException(404, f"no model report for horizon {horizon}d; run src.models.train_baselines")
    return report


@router.get("/models/report")
def model_report(h: int = Query(5, ge=1)) -> dict:
    return data.clean(_horizon_report(h))


def _feature_table(name: str, value_cols: list[str]) -> list[dict]:
    df = data.processed_csv(name)
    if df is None:
        return []
    df = df.copy()
    df["feature"] = df["feature"].str.replace(FEATURE_PREFIX, "", regex=True)
    if "coefficient" in df.columns and "importance" not in df.columns:
        # logistic regression: signed coefficients on standardised features
        df = df.rename(columns={"coefficient": "importance"})
    keep = ["feature"] + [c for c in value_cols if c in df.columns]
    return data.records(df[keep], date_cols=())


@router.get("/models/explainability")
def explainability(h: int = Query(5, ge=1)) -> dict:
    report = _horizon_report(h)
    names = list(report.get("leaderboard", []))
    agreement = data.processed_csv(f"feature_agreement_h{h}d.csv")
    agreement_rows = []
    if agreement is not None:
        agreement_rows = [{"feature": r.feature, "n_models_in_top_n": int(r.n_models_in_top_n),
                           "models": re.findall(r"'([^']+)'", r.models)} for r in agreement.itertuples()]
    return data.clean({
        "horizon": h,
        "models": names,
        "importance": {n: _feature_table(f"importance_{n}_h{h}d.csv", ["importance"]) for n in names},
        "shap": {n: _feature_table(f"shap_{n}_h{h}d.csv", ["mean_abs_shap"]) for n in names},
        "permutation": {n: _feature_table(f"permutation_importance_{n}_h{h}d.csv",
                                          ["importance_mean", "importance_std"]) for n in names},
        "agreement": agreement_rows,
    })


_predictions_cache: dict[int, tuple[tuple, dict]] = {}


def _inputs_signature(h: int) -> tuple:
    """Modification times of everything a prediction depends on."""
    paths = [FEATURES_PATH, *sorted(MODEL_DIR.glob(f"*_h{h}d.joblib"))]
    return tuple((str(p), p.stat().st_mtime_ns) for p in paths)


@router.get("/predictions/latest")
def latest_predictions(h: int = Query(5, ge=1)) -> dict:
    if not any(MODEL_DIR.glob(f"*_h{h}d.joblib")) or not FEATURES_PATH.exists():
        raise HTTPException(404, "no saved models or features; run the pipeline first")
    signature = _inputs_signature(h)
    hit = _predictions_cache.get(h)
    if hit is None or hit[0] != signature:
        hit = (signature, data.clean(predict_latest(horizon=h)))
        _predictions_cache[h] = hit
    return hit[1]


def warm_predictions() -> None:
    """Load the models and score once at startup: the first cold call takes
    ~20s (joblib + XGBoost import), long enough for proxies to give up."""
    try:
        latest_predictions(h=5)
    except Exception:  # noqa: BLE001 - best effort; the endpoint reports real errors
        pass


@router.get("/figures/{name}")
def figure(name: str) -> FileResponse:
    path = data.FIGURES_DIR / name
    if not FIGURE_NAME.match(name) or not path.is_file():
        raise HTTPException(404, "figure not found")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "public, max-age=3600"})
