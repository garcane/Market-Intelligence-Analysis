# CHECKPOINT.md

Running log of stage completions, per the target prompt's checkpoint system. Newest entry first.

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
