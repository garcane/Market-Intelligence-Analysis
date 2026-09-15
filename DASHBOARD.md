# DASHBOARD.md — Interactive Dashboard (Stage 14)

## Running It

```bash
streamlit run dashboard/app.py
```

Requires the pipeline artifacts to already exist (`data/raw/`, `data/processed/`, `outputs/figures/`) — the dashboard is a pure presentation layer and does not fetch data or train models itself. Each section degrades gracefully with a `st.warning` pointing at the missing-prerequisite command if its upstream artifact hasn't been generated yet, rather than crashing.

## Structure

`dashboard/data_loader.py` holds every data-access function, each wrapped in `@st.cache_data` — this is what satisfies the target spec's explicit requirement that the dashboard "consume processed data rather than performing expensive model training on every page load." `dashboard/app.py` is the sidebar-navigated app itself, one function per section.

| Section | Data source | Filters |
|---|---|---|
| Overview | All ingested market prices, `market_stats.py` | — |
| AI Market Overview | `indices_report.json` (Stage 12) | — |
| Company Explorer | `companies.csv` / `company_ai_categories.csv` (Stage 1) | AI category, region |
| Stock Performance | Per-asset OHLCV (Stage 3) | Asset, date range |
| Sentiment Intelligence | `fact_sentiment.parquet` / `news.parquet` (Stage 4) | Sentiment model, label |
| AI Events | `events.csv` / `event_study_report.json` (Stage 11) | Event selector |
| Model Performance | `model_report_h5d.json` (Stage 9), ROC/PR/confusion figures (Stage 13) | — |
| Prediction Analysis | `explainability_report_h5d.json`, `feature_agreement_h5d.csv` (Stage 10) | — |
| Risk Analytics | `indices_report.json` (Stage 12) | — |
| AI Supply Chain | `company_ai_categories.csv` (Stage 1) | Category selector |

## Verification (this is a UI — a passing pytest run alone wouldn't prove it works)

Two layers, since a plain HTTP request to a running Streamlit server only proves the process booted, not that any given page renders without a runtime exception (Streamlit reports app errors client-side over a websocket, invisible to `curl`):

1. **Live server boot**: started `streamlit run dashboard/app.py --server.headless true`, confirmed `GET /_stcore/health` returns `ok` and `GET /` returns HTTP 200.
2. **`tests/test_dashboard.py`** (11 tests) — uses Streamlit's own `AppTest` framework to actually execute the app script and simulate clicking through **every one of the 10 sidebar sections** (Overview + the spec's 9 named sections), asserting no uncaught exception surfaced on any of them. Also manually verified interactively (outside the fixed pytest suite) that selecting a different asset in the Stock Performance dropdown re-renders without error and updates the displayed metrics — proving the filters actually filter, not just render once with defaults.

This caught one real issue during the build: `use_container_width` (used in every `st.dataframe`/`st.image`/`st.line_chart` call) is a Streamlit parameter whose stated removal date (2025-12-31) has already passed as of today — fixed to `width='stretch'` across the whole file rather than ship new code on an already-sunset parameter.

## Stage 14 Completion Check

- [x] All 9 required sections implemented (plus the Overview root, matching the spec's own tree exactly)
- [x] Filtering implemented where it naturally applies (company/sector/country/asset/date/sentiment/AI category, across sections)
- [x] Consumes only processed data — no live fetching or model training on page load
- [x] Actually run and verified (server boot + every section's real render path exercised via `AppTest`), not just imported

**Stage 14 status: COMPLETE.**
