# Market Intelligence Analysis

> An end-to-end financial market intelligence and machine-learning research platform for analysing market behaviour, AI-sector exposure, cryptocurrency markets, financial news and sentiment.

This repository has evolved substantially from its original two-stock Bokeh dashboard. It is now a structured analytical platform with multi-source ingestion, a shared analytical data model, sentiment analysis, feature engineering, time-aware machine learning, explainability, event studies, thematic AI indices and an interactive Streamlit dashboard.

The project is intended as a **research and analytical system**, not an automated trading platform. Model outputs are probabilistic research signals and are not investment advice.

---

## Overview

The current platform connects market data, news and analytical models through a reproducible pipeline:

```text
Market & News APIs
        │
        ▼
┌───────────────────────┐
│   Data Ingestion      │
│ providers + fallback  │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Standardised Data     │
│ prices · news ·       │
│ sentiment · entities  │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Feature Engineering   │
│ technical · momentum  │
│ volatility ·          │
│ cross-sectional ·     │
│ sentiment             │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Target & Temporal     │
│ Validation            │
│ 5-day directional     │
│ classification        │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Model Layer           │
│ Logistic Regression   │
│ Random Forest         │
│ XGBoost               │
│ HistGradientBoosting  │
└───────────┬───────────┘
            │
      ┌─────┴──────────────┐
      ▼                    ▼
Explainability        Financial Analytics
SHAP / permutation    event studies · indices
importance / coeffs   performance · correlation
      │                    │
      └──────────┬─────────┘
                 ▼
        Streamlit Dashboard
```

The analytical model uses explicit dimensions and grain-defined fact tables for companies, markets, dates, news, sentiment, events and model outputs.

---

## Core capabilities

### Multi-source market and news ingestion

The ingestion layer uses provider adapters, validation, retries and fallback logic rather than depending on a single external service.

Implemented providers (`src/ingestion/providers.py`):

- **Yahoo Finance / yfinance** — primary market data for equities *and* crypto
- **CoinCodex** — crypto fallback only (found to drop ~11% of days when used as primary; see `CHECKPOINT.md`)
- **Google News RSS** — key-free news; current headlines only, no historical archive
- **Marketaux** — structured financial news, active only when `MARKETAUX_API_TOKEN` is set

Researched but **not yet implemented** (see `API Reference Documents/`): Finnhub, GDELT and other candidate providers.

Equities currently have no fallback provider — a Yahoo Finance rate limit blocks equity ingestion entirely (observed during the reproducibility test).

Provider quotas, availability, licensing and API terms can change and should be verified before deployment.

### AI and financial market universe

The project maintains a structured universe of public companies, private AI labs and cryptocurrency assets.

The equity taxonomy covers areas including:

- Compute
- Custom AI silicon and networking
- Semiconductor manufacturing
- Memory
- Cloud and AI infrastructure
- Consumer and platform companies
- AI model providers

Companies can have multiple AI-sector classifications through a many-to-many bridge rather than duplicated company records.

The current crypto universe includes BTC, ETH, SOL, XRP, BNB, ADA, DOGE, TRX, LINK and AVAX. SUI, the original project's asset, was deliberately removed from the tracked universe and its legacy CSVs deleted; they remain recoverable from git history.

### News sentiment

News is entity-matched before entering the analytical feature pipeline. Sentiment is stored at article/model grain so multiple methods can be compared on the same articles.

Current sentiment methods include:

- VADER
- TextBlob
- Extensible support for additional models such as FinBERT

### Machine learning

The primary modelling task is a **5-day-ahead directional classification problem**. This replaces the original repository's raw-price regression approach as the primary modelling track.

The current model suite contains:

- Logistic Regression
- Random Forest
- XGBoost
- HistGradientBoosting
- Majority-class baseline
- Random baseline

Preprocessing is fitted on training data only and applied unchanged to validation data. **PR-AUC** is the primary model-selection metric, with ROC-AUC, F1 and Brier score used as secondary measures.

### Explainability

The model layer includes:

- Tree-based feature importance
- Permutation importance
- Logistic Regression coefficients
- SHAP where supported
- Cross-model feature comparison

The aim is to distinguish recurring signals from model-specific artefacts rather than relying on a single importance method.

### Event studies

The analytics layer includes event studies for examining market reactions around manually curated, high-confidence events. Event windows use trading-day positions and abnormal returns relative to a benchmark.

### AI thematic indices

The project constructs equal-weighted thematic indices from the AI company taxonomy, including:

- AI Infrastructure
- AI Platform
- AI Model Provider

These can be compared with independent market benchmarks and other asset classes.

### Interactive dashboard

The Streamlit dashboard provides a unified interface for the project's analytical outputs, including:

1. Overview
2. AI Market Overview
3. Company Explorer
4. Stock Performance
5. Sentiment Intelligence
6. AI Events
7. Model Performance
8. Prediction Analysis (feature importance / SHAP)
9. Risk Analytics
10. AI Supply Chain

Dashboard data access is cached. The dashboard consumes processed outputs rather than retraining models on page load.

---

## Current model results

The current 5-day validation experiment contains 2,826 training rows and 981 validation rows after feature preparation and warm-up filtering.

| Model | Validation PR-AUC | Validation ROC-AUC |
|---|---:|---:|
| XGBoost | **0.409** | 0.579 |
| Random Forest | 0.408 | 0.563 |
| HistGradientBoosting | 0.400 | 0.579 |
| Logistic Regression | 0.397 | **0.583** |
| Majority-class baseline | 0.353 | 0.500 |
| Random baseline | 0.339 | 0.481 |

The results are deliberately reported conservatively. The models provide a modest lift over the naïve baselines rather than demonstrating highly predictive market forecasting. No model produced suspiciously high validation performance; the best validation ROC-AUC was 0.583.

An initial tree-model configuration showed substantial train/validation overfitting. The models were subsequently regularised, reducing the train/validation gap while preserving validation performance.

See [`MODELS.md`](MODELS.md) for the complete methodology, metrics and diagnostic results.

### Robustness and ablation findings

Two follow-up analyses qualify the table above:

- **The top-two ranking is not confident.** Across five random seeds, XGBoost's PR-AUC has a standard deviation of 0.0025, larger than its 0.001 lead over Random Forest. The broader result, that tree ensembles modestly beat Logistic Regression and the baselines, does hold. See [`ROBUSTNESS.md`](ROBUSTNESS.md).
- **Raw PR-AUC misleads across configurations.** It rises with horizon and falls with threshold mostly because the base rate changes. Normalized by base rate, the 1-day horizon shows the highest lift (1.69x), not the 5-day primary horizon.
- **Sentiment does not currently improve prediction.** Market + sentiment scores slightly below market-only (0.397 vs 0.404 PR-AUC), and sentiment alone never predicts a positive. The likely cause is coverage: sentiment exists for well under 1% of rows because the key-free news source has no historical archive. See [`ABLATION_STUDY.md`](ABLATION_STUDY.md).

---

## Repository structure

```text
-Market-Intelligence-Analysis/
│
├── API Reference Documents/       # API architecture and provider documentation
├── data/
│   ├── raw/                       # Raw ingested market/news data
│   ├── processed/                 # Standardised analytical datasets
│   └── reference/                 # Companies, crypto assets, events and taxonomy
│
├── dashboard/
│   ├── app.py                     # Streamlit application
│   └── data_loader.py             # Cached dashboard data access
│
├── notebooks/                     # Exploratory and reporting notebooks
│
├── src/
│   ├── analytics/                 # Indices, event studies and financial analysis
│   ├── features/                  # Feature engineering, targets and splits
│   ├── ingestion/                 # Provider adapters and orchestration
│   ├── models/                    # Dataset construction, training and explainability
│   ├── sentiment/                 # Entity matching and sentiment analysis
│   └── config.py                  # Project configuration
│
├── tests/                         # Unit and end-to-end integration tests
│
├── outputs/
│   ├── figures/                   # Generated analytical visualisations
│   └── model_results/             # Model artefacts and reports
│
├── ABLATION_STUDY.md              # Does sentiment help? Feature-group ablation
├── ANALYSIS_REPORT.md             # Full analytical report
├── CHECKPOINT.md                  # Development and stage-completion log
├── DATA_MODEL.md                  # Analytical star-schema design
├── DASHBOARD.md                   # Dashboard documentation
├── EVENT_STUDY.md                 # Event-study methodology
├── EXPLAINABILITY.md              # Explainability methodology
├── FEATURES.md                    # Feature engineering documentation
├── FINAL_QA.md                    # Final QA audit and Definition of Done
├── INDICES.md                     # AI thematic index methodology
├── MODELS.md                      # Model training and evaluation
├── PERFORMANCE_REVIEW.md          # Pipeline profiling and optimisation
├── PROJECT_AUDIT.md               # Audit of the original repository
├── REPRODUCIBILITY.md             # Clean-environment reproduction test
├── ROBUSTNESS.md                  # Horizon/threshold/seed/asset-group robustness
├── SOFTWARE_ENGINEERING.md        # Architecture and engineering decisions
├── SPLIT.md                       # Temporal split and embargo design
├── TESTING.md                     # Testing strategy and coverage
├── TARGET.md                      # Target-definition methodology
├── UNIVERSE.md                    # AI company and crypto universe
└── VISUALISATION.md               # Visualisation catalogue
```

The original scripts and notebooks are retained under `Old Source Files/` as historical references. They are not the current production pipeline.

---

## Getting started

### 1. Clone the repository

```bash
git clone https://github.com/garcane/-Market-Intelligence-Analysis.git
cd -Market-Intelligence-Analysis
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API credentials

Create a local `.env` file containing the credentials required by the providers you intend to use. Never commit API keys or other secrets.

The test and analytical layers are designed to run independently of live API access where possible.

### 5. Run the test suite

```bash
pytest tests/
```

The latest clean-environment reproduction run passed **137/137 tests** before and after the full pipeline execution.

### 6. Run the analytical pipeline

The main stages are executed as Python modules. The detailed execution sequence is documented in `CHECKPOINT.md` and the relevant stage documents.

```text
Ingestion
   ↓
Sentiment
   ↓
Features
   ↓
Target
   ↓
Temporal split
   ↓
Models
   ↓
Explainability
   ↓
Indices / Event Study / Visualisations
   ↓
Dashboard
```

Exact commands, in order (each stage reads the previous stage's output from `data/`):

```bash
python -m src.ingestion.run_ingestion --assets NVDA,MSFT,TSM,BTC,ETH,SOL --start 2023-06-01
python -m src.sentiment.run_sentiment
python -m src.features.run_features
python -m src.features.run_target
python -m src.models.run_split
python -m src.models.train_baselines
python -m src.models.run_explain
python -m src.models.run_robustness
python -m src.models.run_ablation
python -m src.models.run_model_plots
python -m src.analytics.run_eda
python -m src.analytics.fetch_benchmarks
python -m src.ingestion.run_ingestion --assets AMD,AVGO,AMZN,ORCL,AAPL,GOOGL,META,MU --start 2023-06-01 --skip-news
python -m src.analytics.run_indices
python -m src.analytics.run_event_study
python -m src.analytics.run_sentiment_viz
```

The second ingestion call adds the equities used only by the thematic indices; they are kept out of the six-asset modelling universe (`MODELING_MARKET_IDS` in `src/features/target.py`).

### 7. Launch the dashboard

```bash
streamlit run dashboard/app.py
```

The dashboard has been verified in a clean environment, including its Streamlit health endpoint.

---

## Reproducibility and data integrity

Reproducibility is a core design requirement. The project explicitly addresses common failure modes in financial machine learning:

- **Temporal leakage:** train/validation partitions respect time ordering.
- **Preprocessing leakage:** scalers and encoders are fitted only on training data.
- **Non-stationary raw levels:** raw price/volume levels are excluded from the core ML feature set where appropriate.
- **Target leakage:** target and split columns are explicitly excluded from modelling features.
- **Suspicious model performance:** unusually high AUC triggers a diagnostic rather than being treated as a success.
- **Provider failures:** ingestion uses retry and fallback mechanisms where available.
- **Schema validation:** market and news data are validated before entering downstream stages.
- **Automated testing:** unit and integration tests cover the analytical pipeline.

The current test suite contains **147 automated tests**, including an end-to-end integration test covering the real sentiment → feature → target → split → model chain.

See [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) and [`TESTING.md`](TESTING.md) for the full verification record.

---

## Documentation

The README is intentionally an entry point. Detailed methodology is maintained in dedicated documents:

| Document | Purpose |
|---|---|
| [`UNIVERSE.md`](UNIVERSE.md) | AI company, supply-chain and crypto taxonomy |
| [`DATA_MODEL.md`](DATA_MODEL.md) | Star-schema and fact-table design |
| [`FEATURES.md`](FEATURES.md) | Feature engineering methodology |
| [`TARGET.md`](TARGET.md) | Directional target definition |
| [`SPLIT.md`](SPLIT.md) | Temporal validation design |
| [`MODELS.md`](MODELS.md) | Model training, evaluation and results |
| [`ROBUSTNESS.md`](ROBUSTNESS.md) | Robustness across horizons, thresholds, seeds and asset groups |
| [`ABLATION_STUDY.md`](ABLATION_STUDY.md) | Feature-group ablation: does sentiment help? |
| [`EXPLAINABILITY.md`](EXPLAINABILITY.md) | Feature importance and model interpretation |
| [`EVENT_STUDY.md`](EVENT_STUDY.md) | Event-study methodology |
| [`INDICES.md`](INDICES.md) | AI thematic index construction |
| [`DASHBOARD.md`](DASHBOARD.md) | Streamlit dashboard design |
| [`VISUALISATION.md`](VISUALISATION.md) | Analytical visualisation catalogue |
| [`TESTING.md`](TESTING.md) | Test strategy and coverage |
| [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) | Fresh-environment reproduction results |
| [`PERFORMANCE_REVIEW.md`](PERFORMANCE_REVIEW.md) | Pipeline profiling and optimisation |
| [`ANALYSIS_REPORT.md`](ANALYSIS_REPORT.md) | Full analytical report: findings, limitations, conclusions |
| [`FINAL_QA.md`](FINAL_QA.md) | Final QA audit and Definition of Done checklist |
| [`PROJECT_AUDIT.md`](PROJECT_AUDIT.md) | Audit of the original repository |
| `API Reference Documents/` | External data-source and API architecture |
| [`CHECKPOINT.md`](CHECKPOINT.md) | Development history and stage completion log |

---

## Project status

**Status: Research platform / portfolio project — core pipeline implemented.**

The major analytical stages are implemented and tested, including ingestion, sentiment, feature engineering, target construction, temporal splitting, baseline modelling, explainability, event studies, thematic indices, visualisation and the dashboard.

The architecture remains intentionally extensible. Future work can add provider redundancy, additional sentiment models, richer model families, expanded event datasets and further financial analytics without replacing the core pipeline.

---

## Historical context

The repository began as a small Bokeh application for comparing two stocks with candlestick charts, moving averages and a linear-regression trend line.

That original implementation is retained under `Old Source Files/` for provenance. The earlier XGBoost, LSTM and sentiment notebooks remain useful as research history, but their methodology is not treated as the current production pipeline.

The current repository is a substantial refactor into a structured market-intelligence system with shared ingestion, data modelling, feature engineering, validation and analytical layers.

---

## Disclaimer

This project is intended for **educational, research and portfolio purposes**. It is not financial advice and does not provide guaranteed predictions of future market behaviour.

The models operate on historical and derived data. Historical validation performance does not guarantee future performance, and external data providers may experience outages, rate limits, schema changes or licensing restrictions.

No live automated order execution is implemented by the project.

---

## Author

**garcane**  
GitHub: [@garcane](https://github.com/garcane)
