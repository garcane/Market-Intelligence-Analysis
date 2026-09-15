# VISUALISATION.md — Figure Gallery (Stage 13)

Every figure in `outputs/figures/`, organized by the target spec's Stage 13 categories, with the analytical question it answers (per the spec's instruction: "every chart must answer an analytical question," not exist because it looks impressive) and which earlier stage produced it — Stage 13's job was filling the gaps (model curves, sentiment-over-time/by-sector) that earlier stages hadn't produced yet, not redoing everything from scratch.

## Market (Stage 5)

| Figure | Question it answers |
|---|---|
| `01_price_charts.png` | What did each asset's price actually do over the ingested history? |
| `02_cumulative_returns.png` | How did total return compare across assets on one comparable scale? |
| `03_drawdown.png` | How deep and how long were each asset's worst declines? |
| `04_rolling_volatility.png` | How did realized risk change over time, and how does it compare across assets? |
| `05_return_correlation_matrix.png` | Which assets move together, and which are genuinely diversifying? |

## Sentiment (Stage 5 + Stage 13)

| Figure | Question it answers |
|---|---|
| `06_sentiment_distribution.png` | How do VADER and TextBlob's score distributions compare — do they agree on shape? |
| `07_sentiment_by_company.png` | Which companies' news skews more positive/negative in the current sample? |
| `13_sentiment_over_time.png` *(new)* | Does aggregate sentiment move over the (short, recent) window we have coverage for, and how does that relate to news volume? |
| `13_sentiment_by_sector.png` *(new)* | Does sentiment differ systematically by AI-category (model providers vs. platform vs. compute)? |

## Relationships (Stage 5 + Stage 12)

| Figure | Question it answers |
|---|---|
| `12_index_correlation_matrix.png` | How correlated are the thematic AI indices with each other and with broad-market/crypto benchmarks? |
| `12_rolling_correlation_vs_spx.png` | Has that correlation with the S&P 500 been stable, or has it shifted over the sample window? |
| (sentiment vs. returns) | See `EDA_SUMMARY.md` — reported as **not statistically interpretable** (n=4 overlapping days) rather than a chart that would overstate a relationship the data can't actually support. |

## Models (Stage 9, 10, 13)

| Figure | Question it answers |
|---|---|
| `13_roc_curves.png` *(new)* | How does each model's true/false-positive trade-off compare across the full threshold range? |
| `13_pr_curves.png` *(new)* | How does each model's precision/recall trade-off compare against the class-imbalance baseline? |
| `13_confusion_matrices.png` *(new)* | At the default 0.5 threshold, what specific errors is each model making (and how conservative/aggressive is it)? |
| `10_importance_random_forest.png`, `10_importance_xgboost.png` | Which features does each tree model lean on most (built-in gain-based importance)? |
| `10_importance_logistic_regression.png` | Which features carry the largest standardized coefficients, and in which direction? |
| `10_shap_logistic_regression.png`, `10_shap_xgboost.png` | Per-feature contribution to individual predictions, not just an aggregate ranking |

## Event Analysis (Stage 11 + Stage 13)

| Figure | Question it answers |
|---|---|
| `11_event_nvda_q2fy24_earnings.png`, `11_event_nvda_q4fy24_earnings.png`, `11_event_gpt4o_launch.png`, `11_event_llama31_release.png`, `11_event_deepseek_r1_release.png`, `11_event_deepseek_shock.png` | How did each specific event's abnormal return unfold across the T-5..T+5 window? |
| `11_caar_all_events.png` | Aggregated across all 6 events, is there a consistent pattern in the days immediately around an AI-related market event? |

## What's Deliberately Not Here

- No chart exists purely for visual polish — every figure above is tied to a specific question in the table, per the spec's explicit instruction.
- SHAP for HistGradientBoostingClassifier is absent (the installed `shap` version's `TreeExplainer` doesn't support it) — documented in `EXPLAINABILITY.md`, not silently skipped without explanation.
- No "sentiment by geography" chart — `dim_company.region`/`country` exist in the Stage 1 reference data, but with the current sample's sparse news coverage (163 model-provider articles being the largest single AI-category bucket, per `13_sentiment_by_sector.png`'s underlying data), a further geographic breakdown would mostly be showing noise from very small per-country counts. Worth revisiting once ingestion coverage grows.

## Stage 13 Completion Check

- [x] Market visualizations (price, cumulative return, drawdown, volatility) — Stage 5
- [x] Sentiment visualizations (distribution, by company, over time, by sector) — Stage 5 + this stage
- [x] Relationship visualizations (correlation matrix, rolling correlation, sentiment-vs-returns honestly reported as inconclusive) — Stage 5 + Stage 12
- [x] Model visualizations (ROC, PR, confusion matrices, feature importance, SHAP) — Stage 9/10 + this stage
- [x] Event-window visualizations — Stage 11
- [x] Every chart tied to a stated analytical question

**Stage 13 status: COMPLETE.**
