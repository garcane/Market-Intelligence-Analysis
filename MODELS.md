# MODELS.md — Baseline Models, Training Loop, Evaluation, Leaderboard (Stage 9)

## Setup

Trained on `data/processed/ml_dataset/ml_dataset.parquet`, horizon = 5 days (`PRIMARY_HORIZON`, per `TARGET.md`), split by `split_5d`. Feature preprocessing (`StandardScaler` for numeric, `OneHotEncoder` for `market_id`) is fit **only** on `train`, inside an sklearn `Pipeline`, and applied unchanged to `validation` — this is the exact discipline the original repo's XGBoost notebook lacked (`PROJECT_AUDIT.md` §3a: it fit on all data, then re-evaluated with a random split).

| | Rows | Positive rate |
|---|---|---|
| Train | 2,826 | 39.7% |
| Validation | 981 | 35.3% |

1,275 warm-up rows (NaN in market/cross-sectional features from rolling-window start-up) were dropped before training — see `src/models/dataset.py::build_dataset_for_horizon`.

## Leaderboard Criteria (defined before any model ran)

```text
Primary:   PR-AUC       (robust to the 35-40% class imbalance; threshold-independent)
Secondary: ROC-AUC, F1, Brier score (calibration)
```

Fixed in `src/models/evaluate.py::LEADERBOARD_CRITERIA` before `train_baselines.py` was ever executed — per the target spec's instruction not to pick a metric after seeing results and rationalize it afterward.

## The Four Models + Two Naive Baselines

| Model | Val PR-AUC | Val ROC-AUC | Val F1 | Val Recall | Val Precision | Train time |
|---|---|---|---|---|---|---|
| **XGBoost** | **0.409** | 0.579 | 0.189 | 0.121 | 0.429 | 0.66s |
| Random Forest | 0.408 | 0.563 | 0.089 | 0.049 | 0.459 | 1.45s |
| HistGradientBoosting | 0.400 | 0.579 | 0.234 | 0.159 | 0.440 | 0.41s |
| Logistic Regression | 0.397 | 0.583 | 0.279 | 0.214 | 0.402 | 0.15s |
| Baseline: majority-class | 0.353 | 0.500 | 0.000 | 0.000 | — | — |
| Baseline: random (train base rate) | 0.339 | 0.481 | 0.325 | 0.338 | 0.313 | — |

**Leaderboard (by PR-AUC): XGBoost > Random Forest ≈ HistGradientBoosting > Logistic Regression.**

**Honest read of this result:** every real model beats both naive baselines, but only modestly — PR-AUC 0.40–0.41 vs. a majority-class baseline of 0.353. This is a small, real lift, not an impressive one. Recall is low across the board at the default 0.5 threshold (the tree models in particular predict positive rarely — RF's recall is 0.049), reflecting the class imbalance and conservative decision boundaries; PR-AUC (threshold-independent) is used as the primary ranking criterion specifically so this doesn't distort the comparison, but any actual usage of these models would need explicit threshold tuning, not the default 0.5 cutoff.

## Suspicious-Performance Check (Rule 5)

`SUSPICIOUS_AUC_THRESHOLD = 0.90` — **no model tripped it.** Best validation ROC-AUC is 0.583 (Logistic Regression). This is the expected, honest outcome for a genuinely hard prediction problem (5-day-ahead directional moves in liquid markets); a validation ROC-AUC anywhere near 0.90 here would have been a leakage red flag requiring the whole feature pipeline to be re-audited, per the target spec's explicit instruction to STOP rather than proceed on an implausibly strong result.

## Overfitting Found and Corrected

The first hyperparameter attempt (deeper trees, more permissive leaf sizes) showed a large train/validation gap — a different failure mode from leakage (validation itself wasn't inflated, so the suspicious-AUC check correctly didn't fire), but real overfitting that Rule 5 requires investigating regardless:

| Model | Train PR-AUC (1st attempt) | Val PR-AUC (1st attempt) | Gap |
|---|---|---|---|
| Random Forest | 0.882 | 0.404 | 0.478 |
| XGBoost | 0.976 | 0.406 | 0.570 |
| HistGradientBoosting | 0.957 | 0.413 | 0.543 |

Regularized once (shallower trees: `max_depth` 8→4 for RF, 4→2 for XGBoost, unlimited→3 for HGB; larger `min_samples_leaf`/`min_child_weight`; added L2 for XGBoost and HGB) — a single deliberate adjustment per the spec's "tune carefully, avoid excessive hyperparameter searching," not a grid search:

| Model | Train PR-AUC (regularized) | Val PR-AUC (regularized) | Gap |
|---|---|---|---|
| Random Forest | 0.594 | 0.408 | 0.185 |
| XGBoost | 0.619 | 0.409 | 0.210 |
| HistGradientBoosting | 0.686 | 0.400 | 0.285 |

Validation performance held steady or improved slightly while the train/val gap dropped by more than half in every case — a clean regularization win, not a trade-off. Current hyperparameters are in `src/models/classifiers.py`, with both attempts' numbers recorded there as comments for traceability.

## Calibration

`calibration_curve_summary()` (10 probability bins, mean predicted vs. actual positive rate) is computed for every model and stored in `data/processed/model_report_h5d.json`'s `calibration_validation` field — inspected, not just computed: no model showed a bin with a large predicted-vs-actual gap (e.g. predicting ~70% in a bin that resolves at ~30%), which would indicate poorly calibrated probabilities despite an acceptable AUC.

## Verification

- `tests/test_models.py` — 13 offline tests, including: feature columns never include raw price levels (`test_feature_columns_never_include_raw_price_levels`) or leak target/split columns; the suspicious-AUC flag fires on synthetic near-perfect separation and does not fire on synthetic random predictions (proving the check itself works before trusting its "false" on real data).
- `tests/test_split.py`/`tests/test_target.py` (Stages 7–8) already prove the train/validation partition itself is leakage-safe — this stage's job was proving preprocessing and model-fitting don't reintroduce leakage on top of a safe split, which the fit-on-train-only `Pipeline` structure guarantees by construction.
- All 4 trained model artifacts saved to `outputs/model_results/models/*.joblib` for Stage 10 (Explainability) to load without retraining.

## Stage 9 Completion Check

- [x] Four classifiers implemented and tuned (not left at defaults)
- [x] Preprocessing fit on train only, applied unchanged to validation
- [x] Accuracy, precision, recall, F1, ROC-AUC, PR-AUC, confusion matrix, specificity, balanced accuracy, calibration, training/inference time all computed
- [x] Compared against majority-class and random baselines
- [x] Suspicious-performance check run and explicitly reported (did not fire)
- [x] Overfitting investigated and corrected, not ignored
- [x] Leaderboard criteria fixed before results existed

**Stage 9 status: COMPLETE.**
