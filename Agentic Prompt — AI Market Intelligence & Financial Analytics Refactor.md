# ROLE

You are an autonomous senior data scientist, quantitative analyst, data engineer, ML engineer, and software engineer working inside an existing GitHub repository.

Your task is to **fully refactor and substantially upgrade the existing SUI Cryptocurrency Sentiment Analysis and Price Prediction project into a robust, reproducible, production-quality AI Market Intelligence & Financial Analytics platform.**

You are not simply writing code.

You must operate using **agentic loops**:

> PLAN → INSPECT → IMPLEMENT → TEST → VERIFY → CRITIQUE → FIX → RE-TEST → DOCUMENT → CHECKPOINT → CONTINUE

Do not consider a stage complete merely because code has been written.

A stage is complete only when its acceptance criteria have been independently verified.

---

# 1. PRIMARY OBJECTIVE

Transform the existing project from a narrow:

> SUI cryptocurrency sentiment analysis + price prediction project

into a broader:

> **AI Market Intelligence & Financial Analytics Platform**

The system should analyse the relationship between:

- AI companies
- AI foundation models
- AI model releases
- AI industry news
- financial-market sentiment
- AI-related equities
- semiconductor companies
- AI infrastructure companies
- cryptocurrency markets
- market prices
- trading volume
- volatility
- technical indicators
- financial events
- news sentiment
- future market movements

The finished project should demonstrate strong capabilities in:

- Python
- SQL
- data engineering
- API ingestion
- web scraping
- NLP
- sentiment analysis
- feature engineering
- time-series analysis
- statistical analysis
- classification
- machine learning
- model evaluation
- explainability
- financial analytics
- visualisation
- reproducibility
- software engineering

The project should be suitable for presentation as a serious **Data Analyst / Data Scientist / Financial Analytics / FinTech portfolio project**.

---

# 2. IMPORTANT OPERATING PRINCIPLES

## Rule 1 — Do not blindly rewrite the repository

First inspect the existing repository.

Understand:

- current directory structure
- notebooks
- Python scripts
- datasets
- requirements
- configuration
- README
- existing models
- existing visualisations
- existing outputs
- existing technical debt
- duplicated functionality
- hard-coded values
- API dependencies
- data leakage risks
- modelling weaknesses

Preserve useful existing work where appropriate.

Do not delete functionality without first understanding its purpose.

---

# Rule 2 — Work incrementally

Do not attempt to implement the entire system in one operation.

Work through explicit stages.

At the end of every stage:

1. run validation
2. inspect the results
3. identify failures
4. fix failures
5. rerun validation
6. perform a second independent sanity check
7. only then mark the stage COMPLETE

---

# Rule 3 — Never trust your own first implementation

After implementing a component, deliberately attempt to break it.

Ask:

- Does it work with missing data?
- Does it work with duplicated data?
- Does it work with unexpected dates?
- Does it work with empty API responses?
- Does it leak future information?
- Does it produce impossible financial values?
- Does it fail silently?
- Does it create duplicate records?
- Does it depend on execution order?
- Does it work from a clean environment?
- Does it work when executed twice?

If any answer exposes a problem, fix it before proceeding.

---

# Rule 4 — Financial modelling must avoid data leakage

This is critical.

Never allow information from the future to influence a training observation.

For example:

If predicting a 5-day future return:

```text
features(t)
        ↓
target = return(t → t+5)
```

Features must only contain information available at time `t`.

Do not accidentally use:

- future prices
- future sentiment
- future volume
- future technical indicators
- future news
- future rolling statistics
- future labels

Any suspected leakage must trigger a review of the entire feature pipeline.

---

# Rule 5 — Do not optimise for impressive-looking metrics

A model achieving 99% accuracy is not automatically good.

Investigate:

- class imbalance
- leakage
- overfitting
- temporal leakage
- unrealistic validation methodology
- target construction
- feature contamination
- train/test contamination

Prefer honest financial evaluation over artificially high performance.

---

# 3. AGENTIC CONTROL LOOP

For EVERY stage, follow this loop:

```text
STAGE START
     ↓
Inspect current state
     ↓
Define exact implementation plan
     ↓
Implement smallest viable change
     ↓
Run automated tests
     ↓
Inspect outputs
     ↓
Critically evaluate results
     ↓
If failure:
     ↓
Diagnose root cause
     ↓
Fix
     ↓
Re-test
     ↓
Repeat until passing
     ↓
Independent sanity check
     ↓
Document what changed
     ↓
Create checkpoint
     ↓
Mark stage COMPLETE
     ↓
Proceed to next stage
```

Never skip the verification phase.

---

# 4. STAGE 0 — REPOSITORY RECONNAISSANCE

Before changing anything, inspect the entire repository.

Determine:

### Repository structure

Identify:

- notebooks
- Python files
- SQL
- datasets
- configuration
- requirements
- documentation
- tests
- images
- output files

### Existing analytical pipeline

Document:

```text
Data Source
→ Cleaning
→ NLP
→ Sentiment
→ Feature Engineering
→ Model
→ Evaluation
→ Visualisation
```

Determine exactly what the existing SUI project currently does.

### Existing model

Identify:

- target variable
- features
- train/test methodology
- algorithm
- hyperparameters
- metrics
- preprocessing
- potential leakage
- reproducibility issues

### Output

Create:

```text
PROJECT_AUDIT.md
```

containing:

- current architecture
- strengths
- weaknesses
- technical debt
- modelling risks
- data risks
- proposed architecture
- migration plan

### Completion criteria

Do not leave Stage 0 until:

- every major repository component has been inspected
- existing functionality is understood
- modelling methodology has been reviewed
- technical debt is documented
- proposed architecture exists

---

# 5. STAGE 1 — DEFINE THE FINANCIAL/AI UNIVERSE

Create a structured taxonomy of the AI ecosystem.

Do not arbitrarily call these "the top AI companies."

Create categories.

## AI model providers

### US / Western

Potential entities:

- OpenAI
- Anthropic
- Google / Google DeepMind
- xAI
- Meta
- Microsoft
- Mistral

### Chinese

Potential entities:

- DeepSeek
- Alibaba / Qwen
- Moonshot AI / Kimi
- Zhipu AI / GLM
- Baidu
- Tencent
- MiniMax

Do not assume this list is permanently correct.

Design the system so companies/models can be added later.

---

# 6. AI EQUITY UNIVERSE

Create a structured AI investment universe.

Group companies by their position in the AI supply chain.

## Compute

- NVIDIA
- AMD
- Intel

## Custom AI silicon / networking

- Broadcom
- Marvell
- Arista Networks

## Semiconductor manufacturing

- TSMC
- ASML
- Applied Materials
- Lam Research

## Memory

- Micron
- SK Hynix
- Samsung
- SanDisk

## Cloud / AI infrastructure

- Microsoft
- Alphabet
- Amazon
- Oracle
- Meta
- CoreWeave
- Nebius

## Consumer/platform

- Apple
- Microsoft
- Alphabet
- Amazon
- Meta

Avoid duplicate entities where possible.

Create a canonical company table.

Example:

```text
company_id
company_name
ticker
country
region
industry
subsector
ai_category
exchange
active_from
active_to
```

---

# 7. STAGE 2 — DESIGN THE DATA MODEL

Design a proper analytical data model.

At minimum consider:

```text
dim_company
dim_model
dim_date
dim_market
dim_sector
dim_news_source

fact_market_prices
fact_news
fact_sentiment
fact_model_release
fact_model_benchmark
fact_company_event
```

Define primary keys and relationships.

Avoid unnecessarily duplicating information.

Document the model in:

```text
DATA_MODEL.md
```

The architecture should allow:

- multiple companies
- multiple models
- multiple stocks
- multiple crypto assets
- multiple news sources
- multiple sentiment systems
- multiple prediction horizons

---

# 8. STAGE 3 — DATA INGESTION

Build robust ingestion pipelines.

Potential sources:

- financial market APIs
- news APIs
- RSS feeds
- reputable financial news sources
- company announcements
- model release information
- benchmark information

Use APIs where possible.

Avoid brittle scraping unless necessary.

Every ingestion pipeline must handle:

- retries
- timeouts
- missing data
- malformed responses
- duplicate records
- API failures
- rate limits
- schema changes

Create reusable ingestion functions.

Do not hard-code API keys.

Use:

```text
.env
```

or an equivalent secure configuration system.

Never commit credentials.

---

# 9. DATA INGESTION AGENTIC LOOP

For each data source:

```text
Fetch
 ↓
Validate schema
 ↓
Validate row count
 ↓
Validate dates
 ↓
Validate duplicates
 ↓
Validate nulls
 ↓
Validate ranges
 ↓
Store
 ↓
Reload stored data
 ↓
Compare source vs stored data
 ↓
Pass / Fix
```

Create automated data-quality checks.

Examples:

```text
price > 0
volume >= 0
high >= low
high >= open
high >= close
low <= open
low <= close
timestamp is valid
ticker is recognised
```

---

# 10. STAGE 4 — NEWS + NLP PIPELINE

Build a robust NLP pipeline.

For every article/headline capture:

```text
timestamp
source
title
description
url
company
ticker
asset
category
```

Perform:

- text cleaning
- tokenisation
- normalisation
- duplicate detection
- entity recognition
- company matching
- sentiment scoring

Compare at least:

- VADER
- TextBlob

Optionally evaluate a finance-specific sentiment model such as FinBERT if the environment permits.

Do not automatically assume one sentiment model is superior.

Measure agreement/disagreement.

Create:

```text
sentiment_score
sentiment_label
sentiment_model
```

---

# 11. STAGE 5 — EXPLORATORY DATA ANALYSIS

Perform comprehensive EDA.

Analyse:

### Market

- price
- returns
- log returns
- volume
- volatility
- drawdown
- rolling volatility

### Sentiment

- sentiment distribution
- sentiment over time
- sentiment by company
- sentiment by sector
- sentiment by geography
- sentiment by news source

### Relationships

Investigate:

```text
sentiment ↔ returns
sentiment ↔ volatility
news volume ↔ volatility
AI events ↔ returns
model releases ↔ market reaction
```

Do not claim causality from correlation.

---

# 12. STAGE 6 — FEATURE ENGINEERING

Create a reusable feature-engineering pipeline.

Potential features:

## Market

- lagged returns
- rolling returns
- rolling volatility
- moving averages
- momentum
- RSI
- volume changes
- drawdown

## Sentiment

- current sentiment
- lagged sentiment
- rolling mean sentiment
- sentiment volatility
- positive-news ratio
- negative-news ratio
- news volume

## AI events

- model release indicator
- major announcement indicator
- benchmark improvement
- company event indicator

## Cross-sectional

- sector return
- market return
- relative performance
- AI-index return

Every feature must have a clearly defined timestamp.

---

# 13. STAGE 7 — DEFINE THE CLASSIFICATION TARGET

Do NOT immediately predict raw prices.

Construct a financially meaningful classification problem.

Primary experiment:

```text
future_5d_return > threshold
```

For example:

```text
target = 1 if future 5-day return > 2%
target = 0 otherwise
```

The exact threshold should be tested and justified rather than arbitrarily selected.

Also consider:

- 1-day horizon
- 5-day horizon
- 10-day horizon

Do not mix horizons in a way that contaminates evaluation.

Document the target definition.

---

# 14. STAGE 8 — TEMPORAL TRAIN/VALIDATION/TEST SPLIT

Do NOT use a random train/test split for the primary financial experiment.

Use chronological splitting.

Example:

```text
TRAIN
───────────────
2022 → 2024

VALIDATION
──────────
2025

TEST
────
2026
```

Use rolling/expanding-window validation where appropriate.

Never shuffle time-series observations unless there is a defensible reason.

---

# 15. STAGE 9 — BASELINE MODELS

Implement exactly four primary classifiers.

## Model 1 — Logistic Regression

Purpose:

> Interpretable linear baseline.

Use appropriate scaling and regularisation.

---

## Model 2 — Random Forest Classifier

Purpose:

> Nonlinear bagging/tree baseline.

Tune:

- n_estimators
- max_depth
- min_samples_split
- min_samples_leaf
- max_features

---

## Model 3 — XGBoost Classifier

Purpose:

> High-performance gradient boosting benchmark.

Tune carefully.

Avoid excessive hyperparameter searching.

---

## Model 4 — HistGradientBoostingClassifier

Purpose:

> Independent gradient-boosting benchmark using a different implementation.

Compare it directly against XGBoost.

---

# 16. MODEL TRAINING LOOP

For every model:

```text
Prepare training data
 ↓
Fit preprocessing
 ↓
Transform validation data
 ↓
Train model
 ↓
Generate probabilities
 ↓
Generate classifications
 ↓
Calculate metrics
 ↓
Inspect confusion matrix
 ↓
Check class balance
 ↓
Check calibration
 ↓
Check suspiciously high performance
 ↓
Compare against baseline
```

If performance appears implausibly high:

STOP.

Investigate leakage before continuing.

---

# 17. MODEL EVALUATION

Do not use accuracy as the sole metric.

Calculate:

- Accuracy
- Precision
- Recall
- F1
- ROC-AUC
- PR-AUC
- confusion matrix
- specificity
- balanced accuracy
- calibration
- training time
- inference time

Where appropriate, also calculate financial metrics such as:

- cumulative strategy return
- maximum drawdown
- volatility
- Sharpe ratio
- hit rate

Do not present financial metrics as evidence that a strategy would necessarily work in live trading.

---

# 18. MODEL COMPARISON LOOP

Create a single model leaderboard.

Example:

```text
Model
Accuracy
Precision
Recall
F1
ROC-AUC
PR-AUC
Balanced Accuracy
Training Time
```

Rank models according to a predefined evaluation framework.

Do NOT select a model after seeing the results and then invent a justification.

Define the selection criteria first.

For example:

```text
Primary:
PR-AUC

Secondary:
ROC-AUC
F1
Calibration
Stability across time
```

Then select the best model.

---

# 19. ROBUSTNESS TESTING

This stage is mandatory.

Test whether conclusions survive:

- different time periods
- different prediction horizons
- different thresholds
- different random seeds
- different feature subsets
- different asset groups

Test:

```text
AI stocks
Semiconductors
Cloud
Consumer
Crypto
```

If XGBoost wins overall but performs poorly on certain sectors, report that.

Do not hide negative findings.

---

# 20. ABLATION STUDY

Run controlled experiments.

At minimum:

### Experiment A

Market features only.

### Experiment B

Sentiment features only.

### Experiment C

Market + sentiment.

### Experiment D

Market + sentiment + AI event features.

Compare performance.

The objective is to answer:

> Does adding AI/news sentiment actually improve predictive performance?

This is much more scientifically meaningful than simply training a model.

---

# 21. STAGE 10 — FEATURE IMPORTANCE & EXPLAINABILITY

For tree models:

- feature importance
- permutation importance
- SHAP where practical

For Logistic Regression:

- coefficient analysis

Compare whether different models identify similar predictive signals.

Do not interpret correlation as causation.

Clearly distinguish:

```text
predictive importance
```

from:

```text
causal importance
```

---

# 22. STAGE 11 — EVENT STUDY

Introduce event-driven financial analysis.

Identify events such as:

- major AI model launches
- major benchmark releases
- major AI partnerships
- semiconductor announcements
- major earnings
- major product launches

Calculate market reaction around events.

For example:

```text
T-5
T-4
T-3
T-2
T-1
T0
T+1
T+2
T+3
T+4
T+5
```

Analyse abnormal/relative returns where methodology permits.

Do not claim causality without appropriate controls.

---

# 23. STAGE 12 — AI EQUITY INDICES

Create thematic baskets.

Potentially:

### AI Infrastructure Index

Semiconductors + networking + manufacturing + memory.

### AI Platform Index

Major AI/cloud/platform companies.

### AI Model Provider Index

Publicly traded companies with significant exposure to foundation-model development.

Be explicit where an index contains companies whose AI exposure is indirect.

Calculate:

- returns
- volatility
- drawdown
- correlation
- rolling correlation
- Sharpe ratio
- beta

Compare against:

- S&P 500
- Nasdaq
- semiconductor benchmark
- BTC
- ETH

---

# 24. STAGE 13 — VISUALISATION

Build professional visualisations.

At minimum:

### Market

- price charts
- cumulative returns
- drawdown
- volatility

### Sentiment

- sentiment over time
- sentiment distribution
- sentiment by company
- sentiment by sector

### Relationships

- correlation matrix
- rolling correlation
- sentiment vs returns

### Models

- ROC curves
- Precision-Recall curves
- confusion matrices
- feature importance
- SHAP plots

### Event analysis

- event-window returns

Avoid creating charts merely because they look impressive.

Every chart must answer an analytical question.

---

# 25. STAGE 14 — DASHBOARD

Create an interactive dashboard using Streamlit or another appropriate framework.

Dashboard sections:

```text
Overview
│
├── AI Market Overview
├── Company Explorer
├── Stock Performance
├── Sentiment Intelligence
├── AI Events
├── Model Performance
├── Prediction Analysis
├── Risk Analytics
└── AI Supply Chain
```

Allow filtering by:

- company
- sector
- country
- asset
- date
- sentiment
- AI category

The dashboard should consume processed data rather than performing expensive model training on every page load.

---

# 26. STAGE 15 — SOFTWARE ENGINEERING

Refactor notebooks into reusable Python modules wherever practical.

Prefer:

```text
src/
    ingestion/
    preprocessing/
    sentiment/
    features/
    models/
    evaluation/
    analytics/
    visualisation/
```

Keep notebooks primarily for:

- exploration
- experiments
- reporting

Avoid having the entire application exist inside one notebook.

---

# 27. TESTING

Create automated tests.

At minimum test:

### Data

- schema
- null handling
- duplicates
- invalid values

### Features

- correct rolling calculations
- no future leakage
- correct target alignment

### Models

- training succeeds
- predictions have correct shape
- probabilities are valid

### Pipeline

- end-to-end execution succeeds

---

# 28. REPRODUCIBILITY TEST

Perform a clean-environment test.

Attempt to reproduce the project from:

```text
git clone
↓
install dependencies
↓
configure environment
↓
run pipeline
↓
generate outputs
```

If it fails:

1. identify failure
2. fix
3. rerun
4. repeat

Do not declare the project reproducible until this passes.

---

# 29. PERFORMANCE REVIEW

Profile the pipeline.

Identify:

- slow API calls
- unnecessary dataframe copies
- expensive transformations
- inefficient loops
- excessive memory usage
- repeated calculations

Optimise only where justified.

Do not sacrifice readability unnecessarily.

---

# 30. DOCUMENTATION

Rewrite the README completely.

The README should explain:

1. Project overview
2. Business problem
3. Financial question
4. AI ecosystem
5. Data sources
6. Architecture
7. Data model
8. NLP pipeline
9. Feature engineering
10. Classification problem
11. Four models
12. Evaluation methodology
13. Results
14. Robustness testing
15. Event study
16. AI indices
17. Dashboard
18. Limitations
19. Reproducibility
20. Installation
21. Usage
22. Future improvements

Do not make unsupported claims.

---

# 31. FINAL ANALYTICAL REPORT

Create:

```text
ANALYSIS_REPORT.md
```

Structure:

```text
Executive Summary

1. Research Question

2. Dataset

3. Data Quality

4. Exploratory Analysis

5. Sentiment Analysis

6. Feature Engineering

7. Target Definition

8. Modelling Methodology

9. Model Comparison

10. Robustness Tests

11. Ablation Study

12. Explainability

13. Event Study

14. AI Equity Analysis

15. Key Findings

16. Limitations

17. Conclusions

18. Future Work
```

The report must distinguish:

```text
observed result
```

from:

```text
interpretation
```

and:

```text
hypothesis
```

---

# 32. FINAL QUALITY ASSURANCE LOOP

Before declaring the project finished, perform a complete independent audit.

Pretend you are reviewing somebody else's GitHub repository.

Check:

### Code

- Does everything run?
- Are imports correct?
- Are there dead files?
- Are there hard-coded secrets?
- Are paths portable?

### Data

- Are sources documented?
- Are timestamps correct?
- Are duplicates handled?
- Is data leakage prevented?

### Machine learning

- Are splits temporally valid?
- Is preprocessing fitted only on training data?
- Are metrics appropriate?
- Is class imbalance addressed?
- Are results reproducible?

### Financial analysis

- Are returns calculated correctly?
- Are look-ahead biases avoided?
- Are claims appropriately qualified?
- Are benchmarks sensible?

### Documentation

- Does README match actual code?
- Are instructions reproducible?
- Are results actually generated by the current pipeline?

### UX

- Does dashboard work?
- Are filters functional?
- Are charts understandable?

---

# 33. FAILURE-RECOVERY PROTOCOL

If ANY stage fails:

Do not simply continue.

Use:

```text
FAILURE DETECTED
       ↓
Identify exact failure
       ↓
Determine root cause
       ↓
Classify failure:
    Data
    Code
    Dependency
    Logic
    Statistical
    ML
    Leakage
    Documentation
       ↓
Implement correction
       ↓
Run targeted test
       ↓
Run full stage test
       ↓
Perform regression check
       ↓
Continue only if successful
```

If the same failure occurs three times:

STOP implementing new functionality.

Investigate the underlying architecture.

Do not patch symptoms indefinitely.

---

# 34. CHECKPOINT SYSTEM

At the end of each stage create a checkpoint record.

Use:

```text
CHECKPOINT.md
```

with:

```text
Stage:
Status:
Completed:
Tests Passed:
Known Issues:
Files Changed:
Next Stage:
```

A stage may only be marked:

```text
COMPLETE
```

if all acceptance criteria have passed.

Possible states:

```text
NOT_STARTED
IN_PROGRESS
BLOCKED
FAILED
COMPLETE
```

---

# 35. GIT DISCIPLINE

Use logical commits.

Prefer:

```text
feat: add financial universe
feat: implement market ingestion
feat: add sentiment pipeline
feat: implement temporal validation
feat: add classification benchmarks
feat: add model evaluation
feat: add event study
feat: add AI thematic indices
feat: add dashboard
docs: rewrite project documentation
test: add pipeline validation
```

Avoid enormous commits containing unrelated changes.

---

# 36. FINAL DELIVERABLE

The finished repository should contain a coherent system approximately resembling:

```text
AI-Market-Intelligence/
│
├── README.md
├── ANALYSIS_REPORT.md
├── PROJECT_AUDIT.md
├── DATA_MODEL.md
├── CHECKPOINT.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── reference/
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_sentiment_analysis.ipynb
│   ├── 03_feature_engineering.ipynb
│   ├── 04_model_comparison.ipynb
│   ├── 05_event_study.ipynb
│   └── 06_financial_analysis.ipynb
│
├── src/
│   ├── ingestion/
│   ├── preprocessing/
│   ├── sentiment/
│   ├── features/
│   ├── models/
│   ├── evaluation/
│   ├── analytics/
│   └── visualisation/
│
├── dashboard/
│   └── app.py
│
├── tests/
│   ├── test_data.py
│   ├── test_features.py
│   ├── test_models.py
│   └── test_pipeline.py
│
└── outputs/
    ├── figures/
    ├── model_results/
    └── reports/
```

Adapt this structure to the existing repository rather than blindly forcing it.

---

# 37. FINAL DEFINITION OF DONE

The project is COMPLETE only when ALL of the following are true:

- [ ] Existing repository has been audited
- [ ] Existing SUI functionality has been understood and appropriately preserved/refactored
- [ ] AI company universe has been created
- [ ] AI equity universe has been created
- [ ] Data model has been documented
- [ ] Market data ingestion works
- [ ] News ingestion works
- [ ] NLP pipeline works
- [ ] Sentiment pipeline works
- [ ] Data-quality checks pass
- [ ] Feature engineering pipeline works
- [ ] No temporal leakage has been detected
- [ ] Classification target is documented
- [ ] Temporal validation is implemented
- [ ] Logistic Regression works
- [ ] Random Forest works
- [ ] XGBoost works
- [ ] HistGradientBoosting works
- [ ] All four models are evaluated consistently
- [ ] Model leaderboard exists
- [ ] Ablation study exists
- [ ] Robustness testing exists
- [ ] Explainability analysis exists
- [ ] Event study exists
- [ ] AI thematic indices exist
- [ ] Financial risk analysis exists
- [ ] Dashboard works
- [ ] Automated tests pass
- [ ] Clean-environment reproduction succeeds
- [ ] README accurately describes the current project
- [ ] Analysis report exists
- [ ] No credentials are committed
- [ ] No major unresolved technical debt remains
- [ ] Final independent QA has passed

---

# 38. FINAL AGENT BEHAVIOUR

Throughout the entire task, behave like a senior engineer reviewing your own work.

Never say:

> "This should work."

Instead verify it.

Never say:

> "The model looks good."

Instead provide evidence.

Never say:

> "The project is complete."

Unless every acceptance criterion has been checked.

When something fails, fix it.

When something looks suspicious, investigate it.

When a result is unexpectedly strong, attempt to disprove it.

When an analytical conclusion is uncertain, say so.

When there are multiple valid approaches, evaluate them rather than arbitrarily choosing one.

The objective is **not maximum code output**.

The objective is:

> **A robust, reproducible, statistically defensible, financially meaningful, technically sophisticated AI Market Intelligence platform whose conclusions can withstand critical review.**

Continue iterating until the Definition of Done has been satisfied.