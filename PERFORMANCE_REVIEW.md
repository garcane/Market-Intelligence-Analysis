# PERFORMANCE_REVIEW.md — Pipeline Profiling (target spec §29)

## Method

Wall-clock timed every `run_*.py` orchestrator, then `cProfile`-profiled the outliers to find actual bottlenecks rather than guess. Per the spec's own instruction — "optimise only where justified... do not sacrifice readability unnecessarily" — only changes with profiling evidence behind them were made.

## Before

| Script | Wall time |
|---|---|
| `src.sentiment.run_sentiment` | 5.1s |
| `src.features.run_features` | 2.2s |
| `src.features.run_target` | 1.7s |
| `src.models.run_split` | 2.2s |
| `src.models.train_baselines` | 7.1s |
| **`src.models.run_explain`** | **51–70s (outlier)** |
| `src.analytics.run_indices` | 16.0s |
| `src.analytics.run_event_study` | 17.2s |

## Two Real Fixes, Both Found by Profiling `run_explain.py`

### 1. `permutation_importance(..., n_jobs=-1)` — 57s of pure process-spawn overhead

`cProfile` showed `compute_permutation_importance` spending 56.8 of its 56.9 cumulative seconds inside `process_executor.py:wait_result_broken_or_wakeup` and `reduction.py:dumps` (pickling data to ship to worker processes) — i.e. almost none of that time was the actual permutation computation. `n_jobs=-1` spawns a multiprocessing pool and re-imports the entire sklearn/pandas/numpy stack in every worker, for a computation over ~1,000 validation rows that completes in a couple of seconds single-threaded. Called once per model (4 times), so the overhead was paid 4 times over. **Fixed**: `n_jobs=1` in `src/models/explain.py::compute_permutation_importance`, with the profiling evidence documented inline as a comment so a future reader doesn't "helpfully" re-parallelize it.

### 2. `RandomForestClassifier(n_jobs=-1)` — 47s of pool spawn/teardown *inside the permutation loop*

Fixing (1) alone didn't fully explain the slowdown — a second profile pass showed 47.4 of the remaining ~88s inside `_forest.py:predict_proba` → `pool.py:terminate`, called 217 times. Root cause: `RandomForestClassifier` itself was configured with `n_jobs=-1` in `src/models/classifiers.py` for training speed, but permutation importance calls a fitted model's `predict_proba` **hundreds of times** in a loop (once per shuffle repeat × feature) — and every one of those calls re-spawns and tears down RF's internal joblib process pool. At this dataset size (~2,826 training rows), training is already sub-second single-threaded (confirmed: 1.25s with `n_jobs=-1` removed, barely different from before), so there was no real benefit being traded away — only overhead that got paid on every downstream repeated-inference call. **Fixed**: removed `n_jobs=-1` from both `RandomForestClassifier` and `XGBClassifier` in `classifiers.py` (XGBoost's own native threading doesn't have the same joblib-process-pool-per-call problem, but was left at default for consistency and because it offered no measurable benefit at this scale either).

### Result

| | Before | After |
|---|---|---|
| `src.models.run_explain` wall time | 51–70s | **36.5s** |
| Model leaderboard / metrics | — | **Unchanged** (confirms this was a pure speed fix) |
| Feature importance rankings | — | **Unchanged** (`ai_index_return`, `momentum_10d` still top cross-model-agreed features) |

Retrained models and re-ran the full test suite (137/137 still pass) and the full pipeline chain afterward to confirm the fix changed nothing about correctness, only speed.

## Investigated, Found Reasonable — Not Changed

- **`src.analytics.run_indices` (16.0s) / `run_event_study` (17.2s)**: profiled; the time is genuinely spent on Python's own module-import graph (~4.5–7.8s, unavoidable for a script that imports the full scientific stack) and matplotlib text/font-metrics rendering for annotated heatmap cells (~5.2s) — normal, fixed costs for report-generation scripts that produce text-heavy figures, not an inefficiency in this codebase's own logic. Not worth complicating the plotting code to shave seconds off a script that's run a handful of times per pipeline refresh, not in a hot loop.
- **`.iterrows()` usage** (8 call sites across the codebase): every one iterates over a small reference table or asset list (companies.csv ~33 rows, the universe ~43 rows, a handful to ~17 ingested assets) — negligible overhead at this scale. `src/ingestion/news_data.py::match_entities` does re-scan the full news title list once per company (33 companies × ~280 articles ≈ 9,000 string checks currently) — fine today, flagged here as something to revisit (e.g. a single vectorized pass instead of one pass per company) only if news volume grows by an order of magnitude or more; not changed now per the spec's "do not sacrifice readability unnecessarily" when there's no current performance problem to justify it.
- **DataFrame copies** (`.copy()` calls throughout `src/features/`, `src/models/dataset.py`): deliberate, not accidental — used specifically to avoid `SettingWithCopyWarning` and to keep functions pure (no in-place mutation of a caller's DataFrame), which matters more for correctness/testability at this data scale (thousands, not millions, of rows) than the marginal memory cost of a few extra copies.

## Stage Completion Check (§29)

- [x] Profiled slow scripts rather than guessing
- [x] Found and fixed two real inefficiencies with profiling evidence (not speculative optimization)
- [x] Verified the fixes changed performance only, not correctness (identical results, full test suite still green)
- [x] Declined to "optimize" things that profiled as reasonable, per the spec's explicit instruction not to sacrifice readability without justification

**Performance review status: COMPLETE.**
