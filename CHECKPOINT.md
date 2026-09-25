# CHECKPOINT.md

Running log of stage completions, per the target prompt's checkpoint system. Newest entry first.

---

## Performance Review (§29), Robustness Testing (§19), Ablation Study (§20)

**Status:** COMPLETE

**Gap acknowledged:** Robustness Testing and Ablation Study were unlabeled sections between Stage 9 and Stage 10 in the target spec, deferred when Stages 9-13 were originally built and never clearly flagged as skipped at the time — a real omission, caught only while preparing final documentation and confirmed against the Definition of Done checklist (§37), which lists both as explicit required items. Built properly rather than left as a gap the README/analysis report would otherwise misrepresent.

**Performance Review:** Profiled every `run_*.py` orchestrator; `src.models.run_explain` was a 51-70s outlier. Found and fixed two real inefficiencies: (1) `permutation_importance(n_jobs=-1)` spent 57s spawning multiprocessing pools for a sub-second computation; (2) `RandomForestClassifier(n_jobs=-1)`'s own pool got re-spawned on every one of ~217 repeated `predict_proba` calls inside the permutation loop. Removed unnecessary `n_jobs=-1` from both call sites — cut runtime to 36.5s with results provably unchanged. `PERFORMANCE_REVIEW.md`.

**Robustness Testing:** Tested the Stage 9 XGBoost leaderboard winner across horizons, thresholds, seeds, and asset subgroups. Key finding: raw PR-AUC and PR-AUC-normalized-by-baseline-rate tell **opposite stories** across horizons/thresholds — the 5-day primary horizon is not the "best-performing" in relative terms (1-day has the highest lift over its own baseline, 1.69x). Also found XGBoost's 1st-place margin over Random Forest in `MODELS.md` (0.001 PR-AUC) is smaller than seed-to-seed training noise (std 0.0025) — reported honestly as not a confident result, without discarding the broader "tree ensembles beat Logistic Regression" finding, which does survive. No dramatic equity-vs-crypto subgroup failure found. `ROBUSTNESS.md`.

**Ablation Study:** Answered the spec's central question directly: **sentiment features do not currently improve performance** — sentiment-only scores F1=0.000, and market+sentiment scores slightly *worse* than market-only (0.397 vs 0.404 PR-AUC). Explained why (≈1% sentiment coverage per `FEATURES.md`, not a pipeline defect) rather than left as an unexplained negative result. `ABLATION_STUDY.md`.

**Tests Passed:** `pytest tests/` — 147/147 (10 new tests: `test_robustness.py`, `test_ablation.py`).

**Files Changed:** `src/models/{robustness,run_robustness,ablation,run_ablation,explain,classifiers}.py`, `tests/{test_robustness,test_ablation}.py`, `PERFORMANCE_REVIEW.md`, `ROBUSTNESS.md`, `ABLATION_STUDY.md`.

---

## Reproducibility Test (target spec §28)

**Status:** COMPLETE

**Completed:** Fresh directory + fresh venv reproduction (not a literal `git clone`, since this session's work isn't committed yet — documented as a recommended follow-up). Installed straight from `requirements.txt`, ran the full offline test suite before any data existed (137/137 passed with zero setup beyond pip install), then the full live pipeline chain, then the full suite again. `REPRODUCIBILITY.md`.

**Notable — two real, honestly-reported findings, not hidden:**
1. **Yahoo Finance rate-limited equity ingestion** after this session's heavy cumulative usage — expected external-service behavior, not a code defect. The retry/backoff logic worked exactly as designed and failed loudly rather than silently. Crucially, **crypto ingestion's Yahoo→CoinCodex fallback chain proved itself live** under this real failure condition (not just in unit tests), while surfacing a genuine gap: equities currently have no fallback provider. Already-ingested real data from earlier in the session was substituted to verify the rest of the chain, with the substitution fully disclosed.
2. **A real bug**: `src/models/run_explain.py` was the one figure-producing script missing `FIGURES_DIR.mkdir(parents=True, exist_ok=True)`, silently relying on an earlier script (`run_eda.py`) having already created `outputs/figures/` — an undocumented ordering dependency invisible in the working directory (which had accumulated that directory from many earlier runs) but immediately exposed by a genuinely fresh environment. Fixed; re-verified with results matching `EXPLAINABILITY.md` exactly.

**Tests Passed:** `pytest tests/` — 137/137 in the fresh environment, both before and after the live pipeline run. Result consistency confirmed against the working-directory's documented numbers (identical row/split counts, identical leaderboard ordering, metric values within ordinary floating-point/threading noise).

**Files Changed:** `src/models/run_explain.py`, `REPRODUCIBILITY.md`.

---

## Testing (target spec §27)

**Status:** COMPLETE

**Completed:** `tests/test_pipeline.py` — a genuine end-to-end integration test (synthetic-but-realistic data through the real Stage 4→6→7→8→9 chain), the one thing the module-by-module unit test suite structurally couldn't cover. `TESTING.md` documents the full coverage audit against the spec's checklist.

**Notable — this test earned its place by finding two real bugs on its first run:**
1. `src/features/pipeline.py` produced feature rows *missing* sentiment columns entirely (not NaN) for any asset with no matched news entity, which crashed `src/models/dataset.py`'s imputer — latent in production only because all 6 modeling assets happen to have news coverage. Fixed by always calling `build_sentiment_features` (it already handled "no match" gracefully; the bug was skipping the call).
2. Same failure mode for `sector_return`/`relative_sector_performance` when *no* asset in a batch has a sector match. Fixed by making `impute_sparse_features` create missing sparse columns as NaN before imputing, rather than assuming the upstream pipeline always produced them.
3. A related, adjacent issue surfaced by re-running the live pipeline afterward (not a unit test): Stage 12's additive equity/benchmark ingestion into the same `data/raw/market_prices/` directory made `run_features.py` silently build features for 17 assets instead of 6, correctly tripping `run_split.py`'s strict merge validation. Fixed by introducing an explicit `MODELING_MARKET_IDS` constant that `run_features.py`/`run_target.py` now filter to, rather than implicitly processing "whatever's in the directory."

**Tests Passed:** `pytest tests/` — 137/137. Full pipeline (features → target → split → models → explainability → plots) re-run live after the fixes; results identical to before (`MODELS.md`/`EXPLAINABILITY.md` numbers unchanged), confirming the fixes were pure robustness improvements, not behavior changes.

**Files Changed:** `tests/test_pipeline.py`, `src/features/pipeline.py`, `src/models/dataset.py`, `src/features/target.py` (added `MODELING_MARKET_IDS`), `src/features/run_features.py`, `src/features/run_target.py`, `TESTING.md`.

---

## Stage 15 — Software Engineering

**Status:** COMPLETE

**Completed:** `SOFTWARE_ENGINEERING.md` documents the `src/` layout and the rationale for folding `preprocessing`/`evaluation`/`visualisation` into where they actually live rather than forcing empty top-level packages. Built and **executed** all six target-spec notebooks (`notebooks/01_data_exploration.ipynb` through `06_financial_analysis.ipynb`) — the item explicitly deferred from Stage 5 (confirmed with the user at the time, tracked in `CHECKPOINT.md` so it wasn't forgotten). Every notebook imports and calls tested `src/` functions rather than duplicating logic; none retrain models or re-run ingestion.

**Tests Passed:** All 6 notebooks executed cleanly end-to-end via `jupyter nbconvert --execute` (which fails loudly on any cell error, so a clean write is direct proof of a successful run).

**Notable finding:** the first version of `03_feature_engineering.ipynb`'s live leakage demonstration printed `False` — alarming, given the whole project's Rule 4 emphasis. Investigated immediately rather than dismissed: the cause was `NaN != NaN` always being `True` in pandas, so a plain `==` comparison flagged the RSI feature's structural warm-up NaNs as "different from themselves." The actual `tests/test_features.py` leakage test uses NaN-aware comparison and was correct all along — the bug was in the notebook's own ad-hoc demo code, not the pipeline. Fixed (switched to `Series.equals()`) and re-verified to print `True`.

**Files Changed:** `SOFTWARE_ENGINEERING.md`, `notebooks/*.ipynb` (6 files).

---

## Stage 14 — Dashboard

**Status:** COMPLETE

**Completed:** `dashboard/data_loader.py` (every data-access function `@st.cache_data`-wrapped — no live fetching or training on page load) + `dashboard/app.py`, all 10 sections from the target spec's tree (Overview + 9 named children), with real working filters (asset/date range on Stock Performance, AI category/region on Company Explorer, sentiment model/label on Sentiment Intelligence, category selector on AI Supply Chain, event selector on AI Events). `DASHBOARD.md`.

**Tests Passed:** `tests/test_dashboard.py` — 11 tests using Streamlit's `AppTest` framework to actually execute the app and simulate navigating to all 10 sections, asserting no uncaught exception on any of them (a plain HTTP health check alone wouldn't prove per-section correctness, since Streamlit reports app errors over a websocket, invisible to `curl`). Also manually verified interactively that changing the Stock Performance asset selector re-renders correctly with updated metrics.

**Notable finding:** `use_container_width` (used in every table/image/chart call) is a Streamlit parameter whose stated removal date (2025-12-31) has already passed per the system clock — fixed to `width='stretch'` across the file rather than ship new code already past its own sunset date.

**Files Changed:** `dashboard/{__init__,app,data_loader}.py`, `tests/test_dashboard.py`, `DASHBOARD.md`.

---

## Stage 13 — Visualisation

**Status:** COMPLETE

**Completed:** `src/models/run_model_plots.py` (ROC/PR curves, confusion matrices — the model charts Stage 9 hadn't produced), `src/analytics/run_sentiment_viz.py` (sentiment-over-time, sentiment-by-sector — the sentiment charts Stage 5 hadn't produced), `VISUALISATION.md` consolidating all 26 figures across every stage into one gallery indexed by analytical question, per category, per the target spec's structure.

**Verified:** Full test suite green throughout (no new logic beyond plotting orchestration, verified by direct visual inspection of rendered figures — PR-curve AP scores and confusion-matrix cell counts both cross-checked against Stage 9's `model_report_h5d.json` numbers and matched exactly).

**Known Issues:** No "sentiment by geography" chart — current news sample too sparse per-country for a meaningful breakdown; documented in `VISUALISATION.md` as deferred, not silently dropped.

**Files Changed:** `src/models/run_model_plots.py`, `src/analytics/run_sentiment_viz.py`, `VISUALISATION.md`.

---

## Stage 12 — AI Equity Indices

**Status:** COMPLETE

**Completed:** Expanded ingestion to 8 more equities (AMD, AVGO, AMZN, ORCL, AAPL, GOOGL, META, MU — all already defined in Stage 1's `companies.csv`, just not yet ingested) plus 3 benchmarks (SPX, NASDAQ, SOXX via `src/analytics/fetch_benchmarks.py`) — additive only, doesn't touch the 6-asset ML pipeline. `src/analytics/indices.py` (equal-weighted index construction, Sharpe, beta, drawdown, rolling correlation) + `run_indices.py` + `INDICES.md`. Three thematic indices built from real Stage 1 category membership: AI Infrastructure (NVDA/AMD/AVGO/TSM/MU), AI Platform (MSFT/AMZN/GOOGL/META/AAPL/ORCL), AI Model Provider (MSFT/GOOGL/META — private labs correctly excluded, no public price series).

**Tests Passed:** `pytest tests/` green throughout (12 new tests in `test_indices.py`). Live run: all 14 constituents + 5 benchmarks resolved, zero missing members.

**Notable finding:** AI Infrastructure index's beta vs. the independent SOXX semiconductor ETF benchmark came out to 0.99 — an unplanned but strong internal-consistency check, since the index was built from Stage 1's category membership with no reference to SOXX at all.

**Files Changed:** `src/analytics/{indices,run_indices,fetch_benchmarks}.py`, `tests/test_indices.py`, `INDICES.md`; ingested `data/raw/market_prices/{AMD,AVGO,AMZN,ORCL,AAPL,GOOGL,META,MU,SPX,NASDAQ,SOXX}.parquet`.

---

## Stage 11 — Event Study

**Status:** COMPLETE

**Completed:** `data/reference/events.csv` — 6 manually-curated, real, high-confidence events (not a fabricated or comprehensive catalog; documented rationale for exclusion of anything past this assistant's Jan 2026 knowledge cutoff). `src/analytics/event_study.py` (trading-day-position event windows — not naive calendar arithmetic, avoids the weekend-gap problem; abnormal return vs. SPX benchmark; CAAR aggregation) + `run_event_study.py` + `EVENT_STUDY.md`.

**Tests Passed:** `pytest tests/` green (8 new tests in `test_event_study.py`, including explicit weekend-snapping behavior). Live run: 6/6 events resolved.

**Notable finding — independent real-world verification:** NVIDIA's well-known ~16% single-day pop after Q4 FY24 earnings showed up at **T+1, not T0** (earnings reported after market close) — caught and documented as a real event-study nuance, not hidden. The "DeepSeek shock" event reproduced the widely-reported ~17% single-day NVDA decline almost exactly (measured: -17.0% raw / -15.5% abnormal). Both independently corroborate the curated event dates and the ingested data quality.

**Known Issues:** Simple relative-return abnormal-return methodology (asset return − benchmark return), not a full market-model regression with estimated beta — documented as a deliberate scope simplification in `EVENT_STUDY.md`. A 6-event catalog demonstrates the methodology; it is not a statistically powered study.

**Files Changed:** `data/reference/events.csv`, `src/analytics/{event_study,run_event_study}.py`, `tests/test_event_study.py`, `EVENT_STUDY.md`.

---

## Stage 10 — Feature Importance & Explainability

**Status:** COMPLETE

**Completed:** `src/models/explain.py` (tree importance, permutation importance — the one model-agnostic method shared across all 4 models, LR coefficients, SHAP) + `run_explain.py` + `EXPLAINABILITY.md`.

**Tests Passed:** `pytest tests/` green (7 new tests in `test_explain.py`), including a synthetic-signal-recovery test proving the importance methods actually detect real signal, not arbitrary orderings. Live run against Stage 9's real trained models.

**Notable finding:** `ai_index_return` and `momentum_10d` rank in the top-10 by permutation importance for **all four models** — a genuinely converging signal across different model architectures, not one model's idiosyncrasy. Built-in (gain-based) tree importance disagreed, over-weighting `rolling_vol_30d`/`rolling_vol_7d` — a known bias of gain-based importance toward continuous features, documented as the reason permutation importance (not built-in importance) was used for the cross-model comparison.

**Known Issues:** SHAP not computed for HistGradientBoostingClassifier — unsupported by the installed `shap` version's `TreeExplainer`; documented, not silently skipped. Also `HistGradientBoostingClassifier.feature_importances_` doesn't exist at all (real sklearn limitation) — that model is covered by permutation importance only.

**Files Changed:** `src/models/{explain,run_explain}.py`, `tests/test_explain.py`, `EXPLAINABILITY.md`.

---

## Stage 9 — Baseline Models

**Status:** COMPLETE

**Completed:** `src/models/{dataset,classifiers,baselines,evaluate,train_baselines}.py` + `MODELS.md`. Explicit feature whitelist (not blacklist — the merged ingestion architecture added provider-metadata columns like `asset_id`/`source` that a blacklist would have silently let leak in). Raw price/volume levels deliberately excluded (non-stationary, not scale-comparable across assets). Preprocessing (`StandardScaler`, `OneHotEncoder`) fit only on train, inside an sklearn `Pipeline`. All four required classifiers (Logistic Regression, Random Forest, XGBoost, HistGradientBoosting) plus majority-class and random naive baselines. Leaderboard criteria (PR-AUC primary; ROC-AUC/F1/Brier secondary) fixed in code before any model ran.

**Tests Passed:** `pytest tests/` green (13 new tests in `test_models.py`). Live run on horizon=5d: 2,826 train / 981 validation rows.

**Notable finding — overfitting caught and fixed:** first hyperparameter attempt showed train PR-AUC 0.88–0.98 vs. validation ~0.40 (gap up to 0.57) for the tree models — real overfitting (not leakage; validation itself wasn't inflated, so the automated suspicious-AUC check correctly didn't fire, but Rule 5 still required investigating it). One deliberate regularization pass (shallower trees, larger leaf sizes, added L2) cut the gap by more than half in every case with no loss in validation performance. Final leaderboard: XGBoost (PR-AUC 0.409) > Random Forest (0.408) ≈ HistGradientBoosting (0.400) > Logistic Regression (0.397) — all modestly beat the majority-class (0.353) and random (0.339) baselines; no model tripped the suspicious-AUC (≥0.90) threshold.

**Files Changed:** `src/models/{__init__,dataset,classifiers,baselines,evaluate,train_baselines}.py`, `tests/test_models.py`, `MODELS.md`; trained model artifacts in `outputs/model_results/models/*.joblib`.

---

## Interim — Reconciling a merged-in ingestion architecture

**Status:** COMPLETE (not a numbered stage — unplanned work discovered mid-session)

While working, a merge landed from `origin/main` (remote `github.com/garcane/-Market-Intelligence-Analysis`) adding a provider-adapter ingestion architecture (`src/ingestion/{base,providers,orchestrator,standardize}.py`: retryable provider classes for Yahoo Finance/CoinCodex/Marketaux/Google News with fallback chains and a standardized `article_id`/`published_at` schema). It wraps my original `fetch_market_prices`/`fetch_headlines` functions rather than replacing them, but `validate.py` had been rewritten to the new schema without `run_ingestion.py`'s `ingest_news()` ever converting back to the `fact_news` schema (`news_id`/`timestamp`/`source_id`, per `DATA_MODEL.md` §3.2) that Stages 4–8 all depend on by column name — a real regression, breaking 3 tests.

**Fixed (confirmed with the user: keep the new architecture, reconcile the schema seam):**
- `run_ingestion.py::ingest_news()` now renames the provider layer's `article_id`/`published_at`/`publisher` back to `news_id`/`timestamp`/`source_id` immediately after fetching, before `match_entities`/`validate`/`store` — so the new provider architecture is purely an internal fetch-layer upgrade, invisible to everything downstream.
- `validate.py::validate_news` reverted to require the `fact_news` schema it's actually being handed.
- Found and fixed a **second, independent bug** while smoke-testing the reconciliation: `CoinCodexProvider` was silently failing for every crypto asset (`BTC-USD` passed in, but CoinCodex's API wants bare `BTC`) — always falling back to Yahoo. Fixed the symbol format. This then surfaced a **third issue**: CoinCodex, once actually reachable, returns incomplete history for the tracked crypto assets (131 two-day gaps over ~1,200 days, ~11% of days silently missing) — not caught by `validate_market_prices`, which doesn't check date-completeness gaps. Reordered `default_market_providers` to prefer Yahoo Finance (proven complete throughout Stages 3–8) even for crypto, keeping CoinCodex as fallback only, rather than trust a data source found to silently drop data.
- Minor: fixed a `pd.Timestamp.utcnow()` deprecation warning in `standardize.py`.
- Re-ran the full pipeline end to end (ingestion → sentiment → features → target → split) to regenerate every downstream artifact against the restored complete data, since an earlier smoke-test ingestion run had briefly overwritten `NVDA.parquet`/`BTC.parquet` with a 1-month slice.

**Tests Passed:** `pytest tests/` — 83/83 (was 80/83 immediately after the merge).

**Known Issues:**
- `validate_market_prices` still has no date-completeness/gap check — the CoinCodex issue was caught by manual inspection, not automated validation. Worth adding a gap-check for 24/7-trading assets as future hardening, not done here (time-boxed to reconciling the schema break, not auditing every provider).
- CoinCodex remains wired up as a fallback despite its incompleteness issue — acceptable as a last-resort fallback (better than zero data), but should not become primary again without first adding that gap check.

**Files Changed:** `src/ingestion/{run_ingestion,validate,providers,orchestrator,standardize}.py`; regenerated `data/raw/market_prices/*.parquet`, `data/raw/news/news.parquet`, `data/raw/sentiment/fact_sentiment.parquet`, `data/processed/{features/features,targets/target_table,ml_dataset/ml_dataset}.parquet`.

---

## Stage 8 — Temporal Train/Validation/Test Split

**Status:** COMPLETE

**Completed:**
- `src/models/split.py` — `assign_split` (row-exact embargo using each row's `target_date_{h}d`, not a calendar-day approximation), `add_split_labels` (per-horizon split columns), `walk_forward_folds` (expanding-window utility, seeded now for Stage 19).
- `src/models/run_split.py` — orchestrator: merge Stage 6 features + Stage 7 targets 1:1 on `(market_id, date)` → apply per-horizon split → validate (chronological ordering re-checked independently of the unit tests, on the real merged dataset) → store with round-trip check.
- `SPLIT.md` — full methodology, the concrete embargo example verified against real MSFT data, and live split-count table.
- `tests/test_split.py` — 9 offline tests, most importantly a synthetic-data proof that embargo correctly identifies exactly the rows whose label crosses the split boundary, plus a regression guard that row order is never shuffled.

**Tests Passed:**
- `pytest tests/` — 81/81 passed (full suite, Stages 3–8).
- Live run against real Stage 6/7 data: 6,069 rows merged 1:1 (no silent row loss in the feature/target join — checked explicitly, would raise if the merge dropped anything). Split counts land within a point of the intended 60/20/20 at every horizon (e.g. 5-day: 60.6%/20.0%/18.3%).
- Manually traced one real embargo case end-to-end (MSFT, 5-day horizon): the row dated 2025-05-23 has `target_date_5d = 2025-06-02`, one day past `train_end = 2025-05-31` — correctly labeled `excluded_embargo`, not `train`. This is the subtle leakage vector (label crossing a split boundary) that a naive "just don't shuffle" split would still miss.
- Embargo row counts scale exactly as expected with horizon (12 / 60 / 120 rows at 1d / 5d / 10d — matches the predicted `2 boundaries × h days × 6 assets` formula).

**Known Issues:**
- Boundary dates (`train_end=2025-05-31`, `val_end=2026-01-31`) are fixed constants computed once against the ingestion range at the time of this stage. If the ingested date range changes materially (e.g. a much longer backfill later), these should be recomputed — `SPLIT.md` documents how they were derived so this is a quick redo, not a mystery.
- `walk_forward_folds()` is implemented and unit-tested but not yet wired into any live report — it's prerequisite infrastructure for Stage 19 (Robustness Testing), not used by Stage 9's primary single-split experiment.

**Files Changed:**
`src/features/target.py` (added `target_date_{h}d`), `src/models/{__init__,split,run_split}.py`, `tests/test_split.py`, `SPLIT.md`.

**Next Stage:** Stage 9 — Baseline Models (Logistic Regression, Random Forest, XGBoost, HistGradientBoosting), trained on `split_5d == "train"`, evaluated on `validation`, using this stage's `ml_dataset.parquet` directly.

---

## Stage 7 — Define the Classification Target

**Status:** COMPLETE

**Completed:**
- `src/features/target.py` — `add_future_returns` (the codebase's one deliberately forward-looking function, `.shift(-h)`), `add_classification_targets` (threshold logic, per-horizon thresholds supported), `build_target_table`. Kept structurally separate from `src/features/pipeline.py`'s feature table.
- `src/features/target_analysis.py` — empirical class-balance grid across threshold/horizon candidates, and realized-volatility-by-asset, used to justify (not assert) the threshold choice.
- `src/features/run_target.py` — orchestrator: build → validate (binary values, NaN exactly on the last h rows per asset, no dupes) → store with round-trip check → write class-balance/volatility reports.
- `TARGET.md` — full justification using real computed numbers from the live 6-asset universe: 2% threshold chosen because it's the most class-balanced (28–44% positive across assets) among 0%/1%/2%/3%/5% candidates, and represents 0.21σ–0.55σ of 5-day realized volatility depending on asset (documented as a real heterogeneity limitation, not glossed over). 5-day horizon chosen as the most balanced/least-overlapping among 1d/5d/10d candidates.
- `tests/test_target.py` — 12 offline tests, including a directional regression test (`test_is_genuinely_forward_looking_not_accidentally_backward`) that would catch an accidental `shift(+h)` vs `shift(-h)` sign error — exactly the kind of subtle bug that would otherwise silently break the entire modelling stage.

**Tests Passed:**
- `pytest tests/` — 72/72 passed (full suite, Stages 3–7).
- Live run against real Stage 3 data: 6,069 target rows across 6 assets, all three horizons. Validation confirmed binary-only target values and NaN exactly on each asset's last h rows (e.g. last 5 rows of every asset are NaN for `target_5d`) — no fabricated labels at the edge of the data.

**Known Issues:**
- Threshold heterogeneity across asset classes is real and documented in `TARGET.md`, not fixed here — a single fixed 2% threshold means materially different things (in volatility-normalized terms) for MSFT vs SOL. A volatility-normalized threshold is flagged as a Stage 9 robustness-testing candidate, not implemented as part of the primary experiment (which follows the spec's literal fixed-threshold example).
- No walk-forward/temporal split yet — that's Stage 8, immediately next. The target table itself has no train/test designation.

**Files Changed:**
`src/features/{target,target_analysis,run_target}.py`, `tests/test_target.py`, `TARGET.md`.

**Next Stage:** Stage 8 — Temporal Train/Validation/Test Split (chronological, not random — this is where the Stage 3 XGBoost notebook's original leakage bug from `PROJECT_AUDIT.md` gets explicitly avoided in the new pipeline).

---

## Stage 6 — Feature Engineering

**Status:** COMPLETE (AI event feature category explicitly deferred — see below, not a silent gap)

**Completed:**
- `src/features/market_features.py` — lagged returns, rolling returns, rolling volatility (reused from `market_stats.py`), moving averages, momentum, RSI, volume change/ratio, drawdown (reused). All strictly causal via `.shift()`/right-aligned `.rolling()`.
- `src/features/sentiment_features.py` — current/lagged/rolling sentiment, sentiment volatility, positive/negative ratio, news volume, joined onto each asset's own calendar. No-news days get `news_volume=0` (fact) but `NaN` sentiment (not fabricated neutral).
- `src/features/cross_sectional_features.py` — market return, AI-index return (equity-only), sector return (via `company_ai_categories.csv`), relative performance.
- `src/features/pipeline.py` — combines all three groups into one long table (`market_id`, `date`, features).
- `src/features/{validate,run_features}.py` — schema/duplicate/monotonic-date validation, round-trip storage.
- `src/ingestion/universe.py` — added `entity_to_market_map()`, generalizing an ad-hoc dict that had been hard-coded in Stage 5's `run_eda.py`; refactored `run_eda.py` to use it (removes duplication, and now covers all entities, not just the 5 originally hard-coded).
- `FEATURES.md` — full feature dictionary with formulas, windows, and the AI-event deferral rationale.
- `tests/test_features.py` — 16 offline tests, most importantly `test_market_features_unaffected_by_future_mutation`: mutates all price/volume data after a cutoff and asserts every feature column before the cutoff is byte-identical — the actual proof of Rule 4 compliance, not just a claim of it.

**Tests Passed:**
- `pytest tests/` — 60/60 passed (full suite, Stages 3–6).
- Live run against real Stage 3/4 data: 6,069 feature rows across 6 assets (BTC, ETH, MSFT, NVDA, SOL, TSM), 41 feature columns. Manually spot-checked one row (MSFT, 2023-10-24): `relative_performance` (0.002411) matches `return_1d − market_return` (0.003674 − 0.001263) by hand-calculation.
- Post-warmup null-rate check: `return_1d`, `sma_50d`, `rsi_14d`, `market_return`, `ai_index_return`, `news_volume` are 0% null after each feature's warm-up window — no silent data holes in the parts of the table that should be dense.

**Known Issues:**
- **AI event features are not implemented** — deliberate scope decision (confirmed with the user), documented in `FEATURES.md`, not a bug. No event data source exists (`fact_model_release`/`fact_company_event` were never ingested in Stage 3). Real prerequisite work belongs with Stage 11 (Event Study), which needs the same data.
- `sentiment_current` is non-null for well under 1% of trading days in the live run (real news coverage is sparse relative to years of price history given the key-free RSS source's no-archive limitation — same root cause as the Stage 5 `n=4` relationship-analysis limitation). Downstream modelling stages must handle this as a very sparse feature, not assume dense coverage.
- Cross-sectional benchmarks (`market_return`, `sector_return`) include the asset itself in its own benchmark (equal-weighted, include-self convention) — a known small-universe artifact documented in `FEATURES.md`, not corrected for yet.
- A notebook (`notebooks/01_data_exploration.ipynb` or similar) still does not exist for Stage 5/6 — remains deferred to Stage 15 per the user's earlier decision.

**Files Changed:**
`src/features/{__init__,market_features,sentiment_features,cross_sectional_features,pipeline,validate,run_features}.py`, `src/ingestion/universe.py` (added `entity_to_market_map`), `src/analytics/run_eda.py` (refactored to use it), `tests/test_features.py`, `FEATURES.md`.

**Next Stage:** Stage 7 — Define the Classification Target (this is where the leakage-safety work in this stage gets tested for real: target construction must align `future_5d_return` to features(t) without any overlap).

---

## Stage 5 — Exploratory Data Analysis

**Status:** COMPLETE

**Completed:**
- `src/analytics/market_stats.py` — returns, log returns, rolling volatility (7d/30d), drawdown, cumulative return; all strictly causal (verified — first row of every derived series is `NaN`, never backfilled), reused unchanged by Stage 6's feature pipeline.
- `src/analytics/sentiment_stats.py` — daily sentiment aggregation (mean/volatility/pos-neg ratios/news volume), sentiment-by-entity, label distribution.
- `src/analytics/relationships.py` — same-day sentiment↔return and news-volume↔volatility correlation, explicitly not causal.
- `src/analytics/run_eda.py` — orchestrator producing 7 figures (`outputs/figures/`) and `outputs/reports/EDA_SUMMARY.md`.
- `tests/test_analytics.py` — 9 offline tests, including a regression guard that `return_1d`/`rolling_vol` are `NaN` on their first rows (no look-ahead).

**Tests Passed:**
- `pytest tests/` — 44/44 passed (full suite across Stages 3–5).
- Live run against real Stage 3/4 data: 6 assets (NVDA, MSFT, TSM, BTC, ETH, SOL, 2023-06 → present), 289 scored headlines. All 7 figures generated and visually verified (cumulative-return chart correctly shows SOL's high-beta run-up/drawdown, NVDA's steady climb, MSFT's low volatility relative to crypto).

**Known Issues:**
- Fixed a real encoding bug caught during this stage: report files (`EDA_SUMMARY.md`, JSON reports) were written with `open(..., "w")` with no explicit encoding, which defaults to `cp1252` on Windows and silently corrupted em-dashes into `�`. Fixed by adding `encoding="utf-8"` to every report-writing `open()` call across Stages 3–5.
- Sentiment↔return correlation only has `n=4` overlapping days even after widening the price backfill to "today" — Google News RSS (the key-free source) returns only currently-available headlines with no historical archive, so it cannot be backfilled to match a multi-year price history. The report explicitly flags any `n<10` result as "NOT statistically interpretable" rather than reporting a misleadingly strong correlation (`-0.997` on 4 points) without qualification. A real historical relationship study needs either a historical news source (at the time this said "set `NEWS_API_KEY`", but that variable was never wired to any provider; corrected in the §33–36 entry) or restricting the analysis window to the news source's actual coverage — this is a data-source limitation, not a code bug.
- Sentiment EDA/relationships only run when Stage 4's `fact_sentiment.parquet` exists; script degrades gracefully (logs a warning, skips those sections) if it doesn't, rather than crashing.

**Files Changed:**
`src/analytics/{__init__,market_stats,sentiment_stats,relationships,run_eda}.py`, `tests/test_analytics.py`, `outputs/figures/*.png`, `outputs/reports/EDA_SUMMARY.md`, encoding fix in `src/{ingestion/run_ingestion,sentiment/run_sentiment,analytics/run_eda}.py`.

**Deferred item (tracked, not forgotten):** the target spec's `notebooks/01_data_exploration.ipynb` was not created in Stage 5 — EDA logic lives in `src/analytics/` + `run_eda.py` instead, for testability/reuse/verifiability. Confirmed with the user to defer building the actual notebook(s) to Stage 15 (Software Engineering), which is explicitly where the spec has notebooks reconciled against `src/` modules. Stage 15 must not skip this.

**Next Stage:** Stage 6 — Feature Engineering (reuse `market_stats.py`'s causal-by-construction functions as the base of the leakage-safe feature pipeline).

---

## Stage 4 — News + NLP Pipeline

**Status:** COMPLETE

**Completed:**
- `src/sentiment/text_clean.py` — HTML-unescape + whitespace/CRLF normalization, directly fixing the raw `\r\n`-in-strings bug documented in `PROJECT_AUDIT.md` §3c.
- `src/sentiment/score.py` — dual VADER + TextBlob scoring producing a `fact_sentiment`-shaped long table; corrected, symmetric, gapless label thresholds (fixes the original repo's bug where `[0.4, 0.5)` silently fell through to "Neutral" despite a documented "Slightly Bullish" band covering it).
- `src/sentiment/agreement.py` — Pearson correlation, exact-label agreement, direction agreement, mean abs score diff between the two models.
- `src/sentiment/run_sentiment.py` — orchestrator: score → validate (score range, nulls, dupes) → store with round-trip check → agreement report.
- `tests/test_sentiment.py` — 16 offline tests, including a regression test proving the original threshold gap is fixed, and a test that documents (not "fixes away") a real VADER/TextBlob disagreement on domain-specific negative language.

**Tests Passed:**
- `pytest tests/test_sentiment.py` — 16/16 passed.
- Live run against real Stage 3 news data (289 headlines, 15 companies): produced 578 sentiment rows (289 × 2 models), passed validation and round-trip storage, re-run confirmed idempotent.
- Measured real model disagreement, exactly as the target spec asks for rather than assuming: Pearson correlation ≈0.16, exact-label agreement ≈54%, direction agreement ≈59% between VADER and TextBlob on this data — the two models frequently disagree, most notably on domain-specific negative language ("lawsuit", "fraud", "crashes") that TextBlob's fixed lexicon doesn't recognize as negative but VADER does.

**Known Issues:**
- Entity matching (which company/asset a headline is about) is intentionally naive substring matching, inherited unchanged from Stage 3 — Stage 4 scores sentiment on top of whatever Stage 3 matched, it doesn't re-do entity resolution. Precision/recall of that matching has not been separately measured.
- No FinBERT comparison yet (target spec lists it as optional "if the environment permits") — deferred; VADER vs TextBlob comparison satisfies the mandatory "at least two models" requirement.

**Files Changed:**
`src/sentiment/{__init__,text_clean,score,agreement,run_sentiment}.py`, `tests/test_sentiment.py`.

**Next Stage:** Stage 5 (see above — completed in the same session).

---

## Stage 3 — Data Ingestion

**Status:** COMPLETE

**Completed:**
- `src/config.py` — central config; loads `.env`; auto-fixes a machine-level TLS-interception issue (see Known Issues) via `truststore` (patches Python's `ssl`) and an OS-cert-store export for `curl_cffi` (used internally by `yfinance`).
- `src/ingestion/universe.py` — builds a `dim_market`-shaped frame (equities + crypto) from the Stage 1 reference CSVs; validates no duplicate `market_id`s.
- `src/ingestion/market_data.py` — `yfinance`-based OHLCV fetch with retry/backoff (3 attempts, exponential-ish backoff), timeout, and column normalization.
- `src/ingestion/news_data.py` — Google News RSS ingestion (key-free, structured XML, not HTML scraping) with retry/backoff, plus rule-based entity matching against the company/crypto universe.
- `src/ingestion/validate.py` — schema / row-count / date / duplicate / null / OHLC-range checks for prices; schema / empty-title / duplicate-URL checks for news.
- `src/ingestion/store.py` — parquet storage with fetch→store→reload→compare round-trip verification.
- `src/ingestion/run_ingestion.py` — CLI orchestrator; writes `data/processed/ingestion_report_{market,news}.json`.
- `tests/test_data.py` — 19 offline unit tests (validation logic, round-trip storage, universe integrity). All passing.

**Tests Passed:**
- `pytest tests/test_data.py` — 19/19 passed, no network required.
- Live end-to-end run against real APIs: 6/6 market assets (NVDA, MSFT, TSM, BTC, ETH, SOL) passed fetch→validate→store→reload→compare; news ingestion (3 companies, 60 headlines) passed the same loop.
- Re-ran the full ingestion twice back-to-back to confirm idempotency (Rule 3: "does it work when executed twice?") — identical PASS results both times.
- Deliberately fetched a nonexistent ticker — confirmed it fails cleanly with a `FetchError` after 1 retry rather than silently returning bad data.

**Known Issues:**
- This development machine has antivirus software (Avast) performing TLS interception with its own root CA, which is trusted by Windows but not by Python's bundled `certifi` store — this broke all HTTPS calls (`requests`, `yfinance`) until `src/config.py` was updated to use `truststore` (for plain `requests`/`urllib`) and to export the OS cert store to a PEM bundle for `curl_cffi` (which `yfinance` uses internally and doesn't respect `truststore`). The fix is automatic and Windows-only (no-op elsewhere); flagging it here since it's a real environment condition, not code, and will resurface on any other machine with similar TLS-intercepting security software.
- Found and fixed a data-correctness bug in the round-trip comparison itself during this stage: parquet round-trips can shift `datetime64` unit (e.g. `s` → `ms`) and normalize missing-value sentinels (`pd.NA`/`None` → `NaN`) without changing the actual data — the original naive `DataFrame.equals()` check flagged these as false failures. Fixed by normalizing dates to a common unit and all missing-value sentinels to `NaN` before comparing with `pandas.testing.assert_frame_equal(check_dtype=False)`. Regression tests added (`test_round_trip_tolerates_datetime_unit_change`, `test_round_trip_tolerates_all_null_object_column`).
- Full 43-entity universe (33 companies + 10 crypto assets) has not yet been ingested end-to-end — only a 6-asset + 3-company subset has been live-tested. Korean-exchange tickers (`000660.KS`, `005930.KS`) in particular are unverified against `yfinance` and may need special handling.
- News entity matching is intentionally naive (substring match) per the Stage 2 design note — Stage 4 owns improving precision/recall.
- The two legacy SUI CSVs were removed from the repository (consistent with the confirmed decision to exclude SUI from the tracked crypto universe).

**Files Changed:**
`src/config.py`, `src/ingestion/{__init__,universe,market_data,news_data,validate,store,run_ingestion}.py`, `tests/test_data.py`, `requirements.txt` (added `pyarrow`, `python-dotenv`, `truststore`, `pytest`), `.env.example`, `DATA_MODEL.md` (SUI note correction).

**Next Stage:** Stage 4 — News + NLP Pipeline (sentiment scoring on top of the `fact_news` data this stage now produces).

---

## Stage 2 — Data Model

**Status:** COMPLETE (see `DATA_MODEL.md` for detail)

## Stage 1 — Financial/AI Universe

**Status:** COMPLETE (see `UNIVERSE.md` for detail)

## Stage 0 — Repository Reconnaissance

**Status:** COMPLETE (see `PROJECT_AUDIT.md` for detail)
