# PROJECT_AUDIT.md

Stage 0 — Repository Reconnaissance, per `Agentic Prompt — AI Market Intelligence & Financial Analytics Refactor.md`.

## 1. Current Repository Structure

```text
.
├── README.md                              # describes a generic 2-stock Bokeh dashboard (stale, doesn't match repo)
├── requirements.txt                       # UTF-16 encoded — breaks `pip install -r` in most shells
├── main.py                                # Bokeh candlestick app (2-stock comparison, SMA/linreg overlay)
├── mainxeed.py                            # byte-for-byte duplicate of main.py
├── main_XRP.ipynb                         # scrapes crypto news, scores sentiment (TextBlob + VADER), no ticker filtering
├── main_xgboost copy.ipynb                # XGBoost regression forecast of SUI Close price
├── main_lstm_coindex.ipynb                # ETH LSTM forecaster: STL decomposition, ADF test, walk-forward MC backtest
├── sui_2023-05-09_2025-02-08.csv          # SUI daily OHLCV + market cap, 2023-05-09 → 2025-02-08
├── sui_crypto_headlines_sentiment_analysis.csv  # 108 scraped headlines with TextBlob/VADER/avg scores
└── Fintech Analysis Mapping.pdf           # supporting doc (not yet reviewed in depth)
```

No `src/`, `tests/`, `data/`, `dashboard/`, `.env`, `.gitignore`, or CI config exist. Everything is flat, single-file, notebook-and-script based.

## 2. Existing Analytical Pipeline (as-built)

Three disconnected pipelines currently coexist, each with its own asset, methodology, and no shared code:

```text
Pipeline A (main_xgboost copy.ipynb)
sui_2023-05-09_2025-02-08.csv
  → lag/rolling features on Close
  → XGBRegressor + RandomizedSearchCV (TimeSeriesSplit)
  → predicts raw Close price (regression, not classification)
  → re-evaluated with a RANDOM train_test_split (leakage risk, see §4)

Pipeline B (main_XRP.ipynb)
scrape crypto.news / thecryptobasic / finance.yahoo (unfiltered keyword pages)
  → TextBlob + VADER sentiment per headline
  → sentiment_category via fixed average-score thresholds
  → writes crypto_headlines_sentiment_analysis.csv (never joined to price data)

Pipeline C (main_lstm_coindex.ipynb)
CoinCodex API (ETH) with local parquet/CSV cache
  → STL decomposition, ADF stationarity checks
  → LSTM on log-returns, walk-forward backtest vs auto_arima/naive
  → Monte Carlo forecast with confidence band

Pipeline D (main.py / mainxeed.py)
yfinance → Bokeh candlestick UI for two arbitrary tickers (unrelated to A/B/C)
```

None of these pipelines share ingestion, feature engineering, or evaluation code. None produce a classification target. Sentiment and price data are never merged.

## 3. Existing Model(s) — Audit Detail

### 3a. SUI XGBoost regressor (`main_xgboost copy.ipynb`)
- **Target:** raw `Close` price (regression), not a return or classification target.
- **Features:** lagged Close (1/7/14/30d) + rolling mean/std (7d, 30d) — all backward-looking, correctly time-respecting *when using `TimeSeriesSplit`*.
- **Leakage risk (confirmed):** cell 12 re-splits with `train_test_split(X, y, test_size=0.2, random_state=42)` — a **random** shuffle split on time-series data. Because lag/rolling features make adjacent rows highly autocorrelated, this leaks near-future information into training and inflates the reported test R². This directly violates Rule 4 of the operating prompt and must not be reused.
- **Metric on full-data predictions** in cell 6/7 also reports RMSE/MAE/R² computed on the *same data the model was fit to* (`random_search.fit(X, y)` then `predict(X)`), which is training-set performance dressed as an evaluation metric.
- No baseline comparison, no classification framing, no financial (Sharpe/drawdown) evaluation.

### 3b. ETH LSTM (`main_lstm_coindex.ipynb`)
- Best-engineered piece of the existing codebase: uses log-returns (stationary, ADF-verified), walk-forward folds, Monte Carlo dropout + residual-noise forecast intervals, and benchmarks against `auto_arima` and a naive random walk.
- Still a raw-price/return forecaster, not classification, and lives in total isolation from sentiment/news data.
- Worth preserving as a reference implementation for the future-work "price regression" track, but out of scope for the primary classification pipeline the target prompt calls for.

### 3c. Sentiment pipeline (`main_XRP.ipynb`)
- Headline scraping is **not entity-filtered**: `sui_crypto_headlines_sentiment_analysis.csv` contains headlines about Pump.fun, Coinbase, Mastercard CBDCs, XRP, and Pepe alongside actual SUI headlines — confirmed by inspecting the CSV (only a minority of the 108 rows mention SUI at all).
- Headline text is uncleaned (embedded `\r\n` and leading/trailing whitespace baked into the stored strings).
- Sentiment thresholds for `sentiment_category` are asymmetric/buggy: `0.2 < score < 0.4` is labelled "Slightly Bullish" but a score of exactly `0.4–0.5` or `<0.2 and >-0.2` both fall into "Neutral", meaning part of the intended positive band is silently swallowed into Neutral. This is a logic bug, not just a design choice.
- Sentiment scores are never joined to `sui_2023-05-09_2025-02-08.csv` — no sentiment→price feature pipeline exists yet despite being the project's namesake analysis.
- Web scraping targets (`crypto.news`, `thecryptobasic.com`, Yahoo Finance HTML) are brittle: raw `requests.get` with no retry/backoff/timeout handling beyond a single `timeout=60` on one function, no schema validation, no dedup.

### 3d. Bokeh dashboard (`main.py` / `mainxeed.py`)
- Fully generic (any two `yfinance` tickers), unrelated to SUI/sentiment/AI. Exact duplicate files — dead weight, one must be deleted.
- No caching, no error handling for invalid tickers or empty date ranges.

## 4. Technical Debt & Risk Inventory

| # | Issue | Severity | Notes |
|---|---|---|---|
| 1 | `requirements.txt` is UTF-16 | High | `pip install -r requirements.txt` fails as-is on a clean environment; blocks Stage "reproducibility test" outright |
| 2 | Random train/test split over time-series in XGBoost notebook | High | Direct violation of Rule 4 (temporal leakage) |
| 3 | Train-set-only metrics reported as model performance | High | Misleading, must be replaced with proper held-out evaluation |
| 4 | `main.py` / `mainxeed.py` duplicate | Medium | Dead duplication, delete one |
| 5 | Headline scraping not entity-filtered | High | Sentiment signal is largely noise for the stated "SUI sentiment" purpose |
| 6 | Sentiment/price data never joined | High | Core premise of the "sentiment→price" project is not actually implemented anywhere |
| 7 | Sentiment category threshold logic bug | Medium | Silently mis-buckets a documented "Slightly Bullish" range into "Neutral" |
| 8 | No `.env`/secrets handling | Medium | No API keys currently in code (good), but no config scaffold either |
| 9 | No tests | High | Nothing verifies rolling/lag correctness, target alignment, or schema |
| 10 | README does not describe the repo's actual content | High | README documents an unrelated generic Bokeh app |
| 11 | Brittle scraping with no retry/backoff/dedup | Medium | Violates Stage 3/9 ingestion robustness requirements |
| 12 | No reusable modules (`src/`) | High | Everything is single-file notebooks/scripts, no shared ingestion/feature/model code |
| 13 | No data model / dimensional structure | High | No `dim_company`, `fact_market_prices`, etc. — flat CSVs only |

## 5. What Is Worth Preserving

- **LSTM walk-forward + Monte Carlo methodology** (`main_lstm_coindex.ipynb`) — sound time-series validation practice, reusable as a pattern for later regression/forecast experiments.
- **SUI OHLCV dataset** (`sui_2023-05-09_2025-02-08.csv`) — usable as one seed asset in the new multi-asset data model, once re-ingested through a validated pipeline.
- **Dual-sentiment-model comparison idea** (TextBlob vs VADER) from `main_XRP.ipynb` — directionally correct approach (Stage 4 explicitly wants this), just needs entity filtering, text cleaning, and a corrected threshold scheme.
- **Bokeh candlestick component** — reusable as one visualization building block, not as the project's main interface (target prompt calls for a Streamlit dashboard).

## 6. Proposed Target Architecture

```text
AI-Market-Intelligence/
├── README.md, ANALYSIS_REPORT.md, PROJECT_AUDIT.md (this file), DATA_MODEL.md, CHECKPOINT.md
├── requirements.txt (UTF-8), .env.example, .gitignore
├── data/{raw,processed,reference}/
├── notebooks/  (exploration/reporting only — no production logic lives here)
├── src/{ingestion,preprocessing,sentiment,features,models,evaluation,analytics,visualisation}/
├── dashboard/app.py  (Streamlit, consumes processed data only)
├── tests/{test_data,test_features,test_models,test_pipeline}.py
└── outputs/{figures,model_results,reports}/
```

## 7. Migration Plan (stage sequencing against the target prompt)

1. **Immediate fixes** (blockers for everything else): re-save `requirements.txt` as UTF-8, delete the duplicate `mainxeed.py`, add `.gitignore`.
2. **Stage 1** — define the AI company/equity universe tables (new, greenfield).
3. **Stage 2** — design `DATA_MODEL.md` (dim/fact tables), incorporating the existing SUI OHLCV schema as the template for `fact_market_prices`.
4. **Stage 3** — rebuild ingestion in `src/ingestion/` with retries/validation; re-ingest SUI data through it rather than trusting the existing CSV blindly; add new tickers per the equity universe.
5. **Stage 4** — rebuild the NLP/sentiment pipeline in `src/sentiment/` with real entity filtering, text cleaning, and a corrected threshold scheme; fix or replace the VADER/TextBlob comparison logic; only then join sentiment to price data by date/entity.
6. **Stages 5–14** — proceed as specified in the target prompt (EDA → features → classification target → temporal split → 4 baseline models → evaluation → robustness → ablation → explainability → event study → indices → visualisation → dashboard), all net-new since none currently exist.
7. Retire `main_xgboost copy.ipynb`'s evaluation methodology (keep the feature ideas, discard the random-split evaluation) and keep `main_lstm_coindex.ipynb` as a reference/appendix notebook rather than the primary model track, since the target prompt's primary track is classification, not regression.

## 8. Completion Check (Stage 0 acceptance criteria)

- [x] Every top-level repository component inspected (scripts, notebooks, CSVs, README, requirements, PDF listed but not deep-read — non-code reference doc, low risk)
- [x] Existing functionality understood (4 disconnected pipelines documented above)
- [x] Modelling methodology reviewed, leakage identified (§3a, §4 row 2–3)
- [x] Technical debt documented (§4)
- [x] Proposed architecture defined (§6–7)

**Stage 0 status: COMPLETE.**
