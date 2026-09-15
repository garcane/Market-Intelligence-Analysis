# CHECKPOINT.md

Running log of stage completions, per the target prompt's checkpoint system. Newest entry first.

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
- Sentiment↔return correlation only has `n=4` overlapping days even after widening the price backfill to "today" — Google News RSS (the key-free source) returns only currently-available headlines with no historical archive, so it cannot be backfilled to match a multi-year price history. The report explicitly flags any `n<10` result as "NOT statistically interpretable" rather than reporting a misleadingly strong correlation (`-0.997` on 4 points) without qualification. A real historical relationship study needs either a paid historical news API (`NEWS_API_KEY` in `.env`) or restricting the analysis window to the news source's actual coverage — this is a data-source limitation, not a code bug.
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
