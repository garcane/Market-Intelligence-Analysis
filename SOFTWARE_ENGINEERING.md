# SOFTWARE_ENGINEERING.md — Repository Structure & Engineering Practices (Stage 15)

## `src/` Layout

```text
src/
├── config.py          # paths, secrets (.env), the CURL_CA_BUNDLE/truststore TLS fix
├── ingestion/          # Stage 3: providers, standardize, validate, store, universe
├── sentiment/           # Stage 4: text cleaning, dual-model scoring, agreement
├── analytics/           # Stage 5/11/12/13: EDA, event study, indices, sentiment/model viz
├── features/           # Stage 6/7: market/sentiment/cross-sectional features, target construction
└── models/              # Stage 8/9/10: split, dataset prep, classifiers, evaluation, explainability
```

This adapts the target spec's suggested `preprocessing/`, `evaluation/`, `visualisation/` as top-level packages into where the code actually lives, rather than force empty or single-file packages to exist for their own sake:

- **`preprocessing`** — the target spec's `preprocessing/` maps to `src/models/dataset.py` (feature whitelist, missingness imputation, the sklearn `Pipeline`-based scaler/encoder fit-on-train). It lives next to the models that consume it rather than as a separate top-level package, since nothing else in the codebase needs generic preprocessing independent of the modeling stage.
- **`evaluation`** — maps to `src/models/evaluate.py` (metrics, calibration, the suspicious-AUC check) for the same reason: evaluation logic is tightly coupled to what it evaluates.
- **`visualisation`** — deliberately **not** a single shared module. Plotting lives in each stage's own `run_*.py` orchestrator (`src/analytics/run_eda.py`, `run_indices.py`, `run_event_study.py`, `run_sentiment_viz.py`; `src/models/run_model_plots.py`) because each stage's figures depend on that stage's specific data shape — a shared abstraction would have added indirection without removing duplication (the actual repeated pattern, matplotlib `Agg` backend + `savefig` to `outputs/figures/`, is 3 lines, not worth a module).

Every `run_*.py` follows the same shape: load already-materialized artifacts → compute/validate → save outputs + a JSON/CSV/Markdown report → log a summary. This consistency is itself a form of engineering discipline, even without a shared base class enforcing it — introducing one would be exactly the kind of premature abstraction the project's own guidance warns against for a codebase this size.

## Notebooks: Thin Wrappers Over Tested Modules, Not Duplicated Logic

`notebooks/` holds exactly the six notebooks the target spec's file tree names. Every one of them **imports and calls the same `src/` functions the pytest suite tests** — no notebook re-implements feature engineering, scoring, or model logic inline. This was a deliberate, previously-discussed decision (see `CHECKPOINT.md`'s Stage 5 entry: building the notebooks was explicitly deferred from Stage 5 to Stage 15, confirmed with the user, tracked so it wasn't forgotten).

| Notebook | Calls into |
|---|---|
| `01_data_exploration.ipynb` | `src/analytics/market_stats.py` |
| `02_sentiment_analysis.ipynb` | `src/analytics/sentiment_stats.py`, `src/sentiment/agreement.py` |
| `03_feature_engineering.ipynb` | `src/features/market_features.py` — plus a **live** leakage-safety demonstration on real NVDA data (mutating post-cutoff prices and confirming no pre-cutoff feature value moves), not just a reference to the pytest suite |
| `04_model_comparison.ipynb` | Loads Stage 9's `model_report_h5d.json` (no retraining in the notebook) |
| `05_event_study.ipynb` | `src/analytics/event_study.py`, live on the real "DeepSeek shock" event |
| `06_financial_analysis.ipynb` | Loads Stage 12's `indices_report.json` |

### Every notebook was actually executed, not just written

All six were run end-to-end via `jupyter nbconvert --to notebook --execute --inplace` — `nbconvert` fails loudly (non-zero exit, no output file written) on any cell error, so a clean write is direct proof each notebook runs top-to-bottom against the real pipeline outputs, not just that the `.ipynb` JSON is well-formed.

**This caught a real bug during the build** — not in the pipeline, but in the notebook's own demonstration code. The first version of `03_feature_engineering.ipynb`'s live leakage check used a plain `==` comparison and printed `False`, which looked like a genuine leakage regression (very alarming, given the whole project's Rule 4 emphasis). Investigation showed the cause: `NaN != NaN` is always `True` in pandas, so the comparison flagged the RSI feature's 14-row structural warm-up NaNs as "different from themselves." `tests/test_features.py`'s actual leakage test uses `pandas.testing.assert_series_equal` (NaN-aware) and was correct all along; the notebook's ad-hoc demo code was the sloppy part. Fixed by switching to `Series.equals()` (also NaN-aware) and re-executed to confirm `True`. This is exactly the kind of "don't trust your first implementation, verify" moment the project's operating principles call for — and it happened in documentation/demo code, not production code, which is its own useful data point about where bugs actually tend to hide.

## Stage 15 Completion Check

- [x] `src/` organized into ingestion/sentiment/analytics/features/models, each stage's logic in its own module
- [x] `preprocessing`/`evaluation`/`visualisation` mapped to where they actually belong, with the reasoning documented rather than forced into empty top-level packages
- [x] Notebooks exist for all six named in the target spec's file tree
- [x] Every notebook calls tested `src/` functions rather than duplicating logic
- [x] Every notebook actually executed end-to-end (not just written), and a real bug found in that process was fixed, not hidden

**Stage 15 status: COMPLETE.**
