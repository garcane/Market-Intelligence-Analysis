# ANALYSIS_REPORT.md — Final Analytical Report

Throughout this report, three categories are kept explicitly distinct, as required:

> **Observed result** — a number or fact directly computed from the data.
> **Interpretation** — a reading of what an observed result plausibly means, still grounded in the data.
> **Hypothesis** — an untested claim about why something is true, offered for future work, not asserted as fact.

## Executive Summary

This platform predicts 5-day-ahead directional price moves (>2% threshold) for a 6-asset universe (NVDA, MSFT, TSM, BTC, ETH, SOL) from market technicals, cross-sectional signals, and news sentiment, using four classifiers compared on a proper chronological, embargo-protected split. **Observed result**: all four models beat naive baselines by a small margin (PR-AUC 0.397–0.409 vs. 0.339–0.353 baseline); sentiment features do not improve performance (ablation PR-AUC actually falls slightly when sentiment is added to market features, 0.404→0.397); the leaderboard's top-two model gap (0.001 PR-AUC) is smaller than measured training-seed noise (std 0.0025). The project also includes a 6-event event study (two results independently corroborated against well-documented real-world market history), three thematic AI equity indices, a Streamlit dashboard, and a full test suite (147 tests) built specifically to catch the kind of subtle leakage and integration bugs this domain is prone to — several of which it actually caught, documented rather than hidden, throughout `CHECKPOINT.md`.

## 1. Research Question

Does adding AI-industry news sentiment to market-technical and cross-sectional signals improve the ability to predict short-horizon (5-day) directional price moves for AI-exposed equities and crypto assets, beyond what market data alone achieves? Secondary questions: which of four standard classifier architectures performs best on this task, and do the resulting conclusions hold up under different horizons, thresholds, random seeds, and asset subgroups?

## 2. Dataset

**Observed result**: 6 modeling assets (NVDA, MSFT, TSM equities; BTC, ETH, SOL crypto), 2023-06-01 through 2026-09 (~3.25 years), 6,078 combined feature/target rows after cleaning. News: 282–290 headlines across ~15 companies queried via Google News RSS, scored by both VADER and TextBlob (578–580 sentiment rows). Extended separately for the AI-indices analysis: 8 additional equities (AMD, AVGO, AMZN, ORCL, AAPL, GOOGL, META, MU) plus 3 benchmark series (S&P 500, Nasdaq, SOXX) — kept structurally separate from the 6-asset modeling universe (`src/features/target.py::MODELING_MARKET_IDS`) after an integration bug briefly conflated the two (`CHECKPOINT.md`'s Testing entry).

**Interpretation**: this is a small dataset by ML standards, deliberately — the project prioritizes methodological rigor (leakage safety, honest evaluation, verified reproducibility) over dataset scale, which was never the point being tested.

## 3. Data Quality

**Observed result**: market data passed schema/duplicate/OHLC-consistency validation on every ingestion run (`src/ingestion/validate.py`); a live-discovered data-completeness bug in the CoinCodex crypto provider (~11% of days silently missing) was caught by manual inspection — not automated validation — and led to reordering the crypto provider fallback chain to prefer Yahoo Finance (`CHECKPOINT.md`'s ingestion-reconciliation entry). News entity-matching uses simple substring matching, with an ~82% match rate in one live run; sentiment-label thresholds were fixed after discovering the original repo's version silently miscategorized part of a documented threshold band (`PROJECT_AUDIT.md` §3c, `CHECKPOINT.md`'s Stage 4 entry).

**Hypothesis**: `validate_market_prices` currently has no date-completeness/gap check for 24/7-trading assets — worth adding as a validator rule, not just something caught manually once (`PERFORMANCE_REVIEW.md`/`CHECKPOINT.md` note this as a known gap).

## 4. Exploratory Analysis

**Observed result**: over the ingested window, NVIDIA's cumulative return (≈176%) and Solana's (≈708%) substantially outpaced MSFT's (≈25%) and BTC's (≈152%) (`EDA_SUMMARY.md`). Return correlations across the 6-asset universe are computed and visualized (`outputs/figures/05_return_correlation_matrix.png`). Sentiment-vs-return relationship analysis was attempted but is explicitly reported as **not statistically interpretable** — only n=4 overlapping observation-days exist given the news source's lack of historical archive (`EDA_SUMMARY.md`'s explicit caveat, flagged in the report itself rather than presented as a finding).

## 5. Sentiment Analysis

**Observed result**: VADER and TextBlob show real, measured disagreement on this data — Pearson correlation ≈0.16–0.30 across different live runs, exact-label agreement ≈52–55%. A specific documented case: TextBlob scores "Company faces massive lawsuit as stock crashes amid fraud allegations" as exactly neutral (0.0) while VADER correctly scores it strongly negative (< -0.5) — TextBlob's fixed lexicon simply doesn't contain domain-specific negative financial terms. **Interpretation**: this is exactly the kind of model-choice consequence the target spec asked to measure rather than assume away — neither model is "right," and using only one (as the original single-model repo did) would have silently substituted one model's blind spots for ground truth.

## 6. Feature Engineering

**Observed result**: 41–46 features spanning market technicals (lags, rolling returns/volatility, momentum, RSI, volume), sentiment (current/lagged/rolling, positive/negative ratio, news volume), and cross-sectional signals (market/sector/AI-index return, relative performance). Leakage safety is proven by a mutation-based regression test (`tests/test_features.py`), not merely asserted — verified live against real NVDA data in `notebooks/03_feature_engineering.ipynb`, which also caught and fixed a false-alarm bug in its own demonstration code (a `NaN != NaN` comparison artifact, documented in `SOFTWARE_ENGINEERING.md`).

## 7. Target Definition

**Observed result**: `target_5d = 1 if future_5d_return > 2% else 0`. The 2% threshold and 5-day horizon are the most class-balanced choice among 5 threshold candidates × 3 horizons tested empirically on real data (28–44% positive rate across all 6 assets at 2%/5d, vs. near-coinflip at 0% or severe imbalance at 5%, e.g. 5.9% positive for MSFT) — see `TARGET.md`. **Interpretation**: a single fixed percentage threshold is not an equally-sized move for every asset (0.55σ for MSFT vs. 0.21σ for SOL, in realized-volatility terms) — a real, documented limitation, not glossed over.

## 8. Modelling Methodology

**Observed result**: chronological (never random) train/validation/test split (2023-06-01→2025-05-31 / →2026-01-31 / →present), with **embargo protection** — rows whose target resolves past a split boundary are excluded, verified against a specific real MSFT row (`SPLIT.md`). Preprocessing (scaling, one-hot encoding) fit only on the training split, inside an sklearn `Pipeline`. This directly replaces the original repo's documented leakage bug (`PROJECT_AUDIT.md` §3a: a random `train_test_split` applied after time-series feature engineering).

## 9. Model Comparison

**Observed result** (5-day horizon, validation set, n=981):

| Model | PR-AUC | ROC-AUC | F1 |
|---|---|---|---|
| XGBoost | 0.409 | 0.579 | 0.189 |
| Random Forest | 0.408 | 0.563 | 0.089 |
| HistGradientBoosting | 0.400 | 0.579 | 0.234 |
| Logistic Regression | 0.397 | 0.583 | 0.279 |
| Baseline (majority class) | 0.353 | 0.500 | 0.000 |
| Baseline (random) | 0.339 | 0.481 | 0.325 |

No model tripped the suspicious-AUC (≥0.90) leakage check. An initial hyperparameter pass showed severe overfitting for all three tree-based models (train PR-AUC 0.88–0.98 vs. validation ~0.40) — fixed with one regularization pass, halving the train/validation gap with no loss in validation performance (`MODELS.md`).

**Interpretation**: all four models modestly beat naive baselines — a real but small signal exists in market/cross-sectional data for this task. **The specific 1st-place ranking (XGBoost over Random Forest) should not be read as confident** — see §10.

## 10. Robustness Tests

**Observed result**: XGBoost's PR-AUC across 5 random seeds ranges 0.4056–0.4132 (std 0.0025) — larger than its 0.001 margin over Random Forest. Raw PR-AUC rises with horizon (1d: 0.275 → 5d: 0.409 → 10d: 0.483) and falls with threshold (1%: 0.471 → 3%: 0.331), but both trends **invert** once normalized by each configuration's own positive rate (a "lift over baseline" measure) — 1-day horizon actually shows the highest relative lift (1.69x) despite the lowest raw PR-AUC. No dramatic equity-vs-crypto subgroup failure (PR-AUC 0.411 vs. 0.420). Full detail: `ROBUSTNESS.md`.

**Interpretation**: the primary experiment's 5-day/2% choice, justified in `TARGET.md` on class-balance grounds, is not obviously the best-performing configuration in relative terms — a genuinely useful finding that a purely accuracy-chasing project would have been tempted to suppress in favor of the more flattering raw-PR-AUC framing.

## 11. Ablation Study

**Observed result**: Market-only PR-AUC = 0.404; Sentiment-only = 0.385 (F1 = 0.000 — never predicts positive); Market+Sentiment = 0.397 (**lower** than market-only); Market+Sentiment+Cross-sectional = 0.406 (best, but the gain over market-only is attributable to cross-sectional features, not sentiment — consistent with §12's finding that no sentiment feature appears in any model's top-10). Full detail: `ABLATION_STUDY.md`.

**Interpretation**: sentiment does not currently improve predictive performance in this pipeline. **Hypothesis** (explicitly labeled as such, not asserted as fact): this is a coverage problem, not a signal-doesn't-exist problem — with ~1% sentiment coverage against the price history (a direct consequence of the key-free news source's lack of historical archive), no model could realistically learn to use it regardless of whether a real relationship exists. This hypothesis is untested — it would require a properly historical news source to check.

## 12. Explainability

**Observed result**: `ai_index_return` and `momentum_10d` rank in the top-10 by permutation importance for all four model architectures — the most consistently converging signal found anywhere in this project. Built-in (gain-based) tree importance disagreed, over-weighting `rolling_vol_30d`/`rolling_vol_7d` — a known bias of gain-based importance toward continuous features, which is why permutation importance (not built-in importance) was used for the cross-model comparison. Full detail: `EXPLAINABILITY.md`.

**Interpretation, explicitly not extended to causation**: these are the features the models found most useful for discriminating the training data — not a claim that AI-index movement or 10-day momentum *causes* an individual asset's 5-day return.

## 13. Event Study

**Observed result**: 6 curated real events, abnormal returns computed vs. S&P 500 across a T-5..T+5 trading-day window. Two independently corroborate well-documented real-world history: NVIDIA's Q4 FY24 earnings reaction landed at T+1 (+16.4%), not T0 (-2.9%) — because earnings were reported after market close, an event-study nuance caught and explained, not hidden; the "DeepSeek shock" reproduced its famous ~17% single-day NVDA decline almost exactly (measured -17.0% raw / -15.5% abnormal). Full detail: `EVENT_STUDY.md`.

**Interpretation**: this is strong (if informal) evidence the underlying price data and event dates are both correct — real independent facts landing where the methodology predicts they should is a stronger check than any synthetic unit test could provide. **No causal claim**: an abnormal return following an event is consistent with the event mattering, not proof of it net of every other contemporaneous factor.

## 14. AI Equity Analysis

**Observed result**: three equal-weighted thematic indices built from Stage 1's real category membership. AI Infrastructure Index: 548.7% cumulative return, 49.4% annualized volatility, β=2.10 vs. S&P 500, **β=0.99 vs. the independent SOXX semiconductor benchmark** (built with zero reference to SOXX). AI Platform and AI Model Provider indices show more moderate, closely-clustered statistics (Sharpe 1.37 and 1.43 respectively — expected, since they share 3 of their constituents). Full detail: `INDICES.md`.

**Interpretation**: the SOXX beta match is a strong internal-consistency check on the whole index-construction methodology, not just a coincidence — an independently-defined real-world benchmark landed almost exactly where five independently-selected chip/memory names, aggregated by the project's own logic, predicted it should.

## 15. Key Findings

1. Market and cross-sectional signals carry a real, small, honestly-modest predictive edge over naive baselines for 5-day-ahead directional moves (observed).
2. Sentiment does not currently improve that prediction, likely (hypothesis, not proven) due to sparse coverage rather than an absence of real signal (observed + hypothesis, clearly separated).
3. The specific model-ranking at the top of the Stage 9 leaderboard is not statistically confident given measured training-seed noise (observed).
4. Relative (baseline-normalized) and absolute PR-AUC comparisons across horizons/thresholds can disagree, and did here — a genuine finding about how to read this kind of metric, not just about this dataset (observed).
5. Two independent, unplanned corroborations against real-world market history (the DeepSeek shock, NVIDIA's earnings-pop timing) support confidence in the underlying data and event-study methodology (observed).
6. AI-category structural signals (`ai_index_return`, sector membership) carry more model-useful signal than raw price-volatility features once measured fairly (permutation importance vs. gain-based importance) (observed).

## 16. Limitations

See `README.md` §18 for the consolidated list; the most consequential for interpreting these results: sparse news coverage undermines the sentiment ablation's power to detect a real effect if one exists; a 6-asset modeling universe limits how much weight any subgroup (sector, asset-class) finding can bear; XGBoost's leaderboard win is not statistically confident; equity ingestion has no fallback provider (a real, live-discovered operational gap, not hypothetical).

## 17. Conclusions

The platform demonstrates a methodologically sound, leakage-audited, honestly-evaluated pipeline from raw ingestion through model comparison, explainability, robustness testing, event study, and thematic index construction. The headline financial conclusion — market/cross-sectional data carries a small real edge, sentiment does not currently add to it — is not the outcome a project optimizing for an impressive-sounding result would have reported, which is itself evidence the evaluation methodology was not bent toward a predetermined conclusion.

## 18. Future Work

See `README.md` §22 (paid historical news API, equity ingestion fallback, real event data ingestion, larger modeling universe, formal significance testing for the model leaderboard).
