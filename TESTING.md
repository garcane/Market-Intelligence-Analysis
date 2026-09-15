# TESTING.md — Automated Test Suite (target spec §27)

## Coverage Against the Spec's Checklist

| Category | Required | Covered by |
|---|---|---|
| **Data** | schema, null handling, duplicates, invalid values | `tests/test_data.py` (19 tests) |
| **Features** | correct rolling calculations, no future leakage, correct target alignment | `tests/test_features.py` (16, incl. the mutation-based leakage proof), `tests/test_target.py` (12), `tests/test_split.py` (9) |
| **Models** | training succeeds, predictions correct shape, probabilities valid | `tests/test_models.py` (13), `tests/test_explain.py` (7) |
| **Pipeline** | end-to-end execution succeeds | `tests/test_pipeline.py` (3) — added this stage; see below for why it was a real gap, not just a checklist formality |
| *(not in the spec's list, added anyway)* | Dashboard renders without runtime error | `tests/test_dashboard.py` (11) — a UI has no meaning to "unit test" the way a function does; `AppTest` is the closest equivalent |

**137 tests total, all passing** (`pytest tests/`).

## Why `test_pipeline.py` Mattered: Two Real Bugs Found, Not Zero

Every other test file exercises one module against a fixture shaped exactly right for that module — which proves each module is internally correct, but provably cannot catch a mismatch at the *boundary* between two modules (a fixture built by hand is definitionally always shaped correctly). `test_pipeline.py` instead runs synthetic-but-realistic data through the actual chain of real functions, catching two genuine integration bugs on its first run:

1. **`sentiment_current` and other sentiment columns went missing (not NaN) when an asset had no matched news entity.** `src/features/pipeline.py` only called `build_sentiment_features` when `entity_id is not None`, so an unmatched asset's feature row simply lacked those columns rather than having them NaN-filled — which then crashed `src/models/dataset.py::impute_sparse_features` with a `KeyError` the moment such an asset appeared. Currently latent in production only because all 6 modeling assets happen to resolve to a matched entity. **Fixed**: always call `build_sentiment_features` (it already handles "no match" gracefully by returning NaN-filled columns); the bug was skipping the call entirely rather than trusting the callee's existing behavior.
2. **The same failure mode for `sector_return`/`relative_sector_performance`** when *no* asset in a batch has an AI-category sector match (e.g. crypto-only batch). **Fixed**: `impute_sparse_features` now creates any entirely-missing sparse column as NaN before imputing, rather than assuming the upstream feature pipeline always produced it — moving the robustness guarantee to the layer that should own it (the function whose whole job is "handle sparse/optional features").

A third, adjacent issue surfaced by actually *running* the modeling pipeline again after these fixes (not by a unit test, but by the "does it still work end to end" discipline this whole project has followed): Stage 12's additive ingestion of index-analysis equities and benchmark series into the same `data/raw/market_prices/` directory the modeling pipeline reads from meant `run_features.py` started building features for 17 assets instead of 6, and `run_split.py`'s feature/target merge (deliberately strict — `validate="one_to_one"` plus an explicit row-count check) correctly refused to silently proceed on the resulting mismatch. **Fixed** by making the classification-modeling universe an explicit constant (`src.features.target.MODELING_MARKET_IDS`) that `run_features.py`/`run_target.py` filter to, rather than implicitly processing "whatever's in the directory" — the directory now legitimately serves two purposes (modeling + index analysis) and the code no longer assumes it serves only one.

All three fixes are covered by regression tests (`test_pipeline.py::test_sparse_columns_survive_when_no_asset_in_batch_has_a_match`, plus the full end-to-end test itself now using real tickers to exercise the actual universe-lookup code paths) and the full pipeline was re-run live end to end afterward to confirm identical results to before (`MODELS.md`/`EXPLAINABILITY.md`'s numbers are unchanged).

## What Full Live Verification Looked Like (Beyond `pytest`)

Nearly every stage in this project was additionally run against real data via its `python -m src.X.run_Y` CLI at least once (documented per-stage in `CHECKPOINT.md`), not just covered by offline unit tests — real network ingestion, real sentiment scoring on real headlines, real model training with results cross-checked against independently known facts (the DeepSeek shock and NVIDIA earnings-pop event-study results in `EVENT_STUDY.md`, the SOXX beta≈0.99 sanity check in `INDICES.md`). `pytest` proves the code is correct in isolation; these live runs proved it's correct in practice — the target spec's Rule 3 ("never trust your own first implementation... does it work from a clean environment") is about exactly this gap between the two.

## Stage Completion Check (§27)

- [x] Data: schema, null handling, duplicates, invalid values
- [x] Features: correct rolling calculations, no future leakage, correct target alignment
- [x] Models: training succeeds, predictions correct shape, probabilities valid
- [x] Pipeline: end-to-end execution succeeds — genuinely verified, not just asserted, and it found real bugs
- [x] Full suite passing: 137/137

**Testing stage status: COMPLETE.**
