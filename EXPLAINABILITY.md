# EXPLAINABILITY.md — Feature Importance & Explainability (Stage 10)

**Everything below is predictive importance — which features the models actually use to discriminate the training data — never causal importance. No claim here should be read as "X causes the 5-day return to move."** The target spec is explicit that these are different things.

## Methods Used

| Method | Models | Notes |
|---|---|---|
| Built-in importance | Random Forest, XGBoost | Gain/impurity-based; not available for HistGradientBoostingClassifier (a real sklearn limitation) |
| Permutation importance | All four | Model-agnostic — same interface, same validation-set scoring (PR-AUC drop when a column is shuffled) for every model, so it's the fair basis for cross-model comparison |
| Standardized coefficients | Logistic Regression | `\|coefficient\|` on scaler-transformed features, directly comparable in magnitude |
| SHAP | Logistic Regression, XGBoost | Mean `\|SHAP value\|` on a 300-row validation sample (HistGradientBoostingClassifier isn't supported by the installed `shap` version's `TreeExplainer` — skipped, not silently faked) |

## Cross-Model Agreement (the headline result)

Using permutation importance (the one method every model shares), two features land in the top-10 for **all four models**:

| Feature | Models agreeing (top-10) |
|---|---|
| **`ai_index_return`** | Logistic Regression, Random Forest, XGBoost, HistGradientBoosting (4/4) |
| **`momentum_10d`** | Logistic Regression, Random Forest, XGBoost, HistGradientBoosting (4/4) |
| `lag_return_1d` | Random Forest, XGBoost, HistGradientBoosting (3/4) |
| `market_return` | Logistic Regression, XGBoost, HistGradientBoosting (3/4) |
| `rolling_return_10d` | Random Forest, XGBoost, HistGradientBoosting (3/4) |
| `return_1d` | Logistic Regression, Random Forest, XGBoost (3/4) |

Full table: `data/processed/feature_agreement_h5d.csv`.

**Reading this honestly:** the cross-sectional AI-equity benchmark (`ai_index_return`, from Stage 6) and short-term price momentum are the most consistently used signals across every model architecture tested — a genuinely converging result, not an artifact of one model's particular biases. Sentiment features do not appear in any model's top 10, consistent with `FEATURES.md`'s documented finding that `sentiment_current` is non-null for well under 1% of rows in the current data — there simply isn't enough sentiment coverage yet for models to have learned to use it.

## Method Disagreement (also worth reporting honestly)

Built-in (gain-based) importance for the tree models ranks `rolling_vol_30d`/`rolling_vol_7d` far above everything else (XGBoost: 0.060 and 0.056, roughly 25% higher than the next feature) — but these barely register in permutation importance. This is a known, real phenomenon: gain-based importance is biased toward continuous, high-cardinality features (volatility is smoothly distributed; a one-hot `market_id` column is not), which inflates their apparent importance without meaning they actually drive validation-set predictive power. Permutation importance measures the latter directly, which is why it — not built-in importance — is used for the cross-model agreement comparison above.

One structural signal is worth flagging separately: `sector_return_missing` (whether an asset has an AI-category peer group at all — true for equities, false for crypto, per `FEATURES.md`'s cross-sectional design) ranks 8th in XGBoost's built-in importance. This is a legitimate, interpretable finding — equities and crypto behave differently enough that "which asset class is this" carries real signal — not a leakage artifact (the flag reflects the asset's fixed category, not any future information).

## Logistic Regression Coefficients (directly interpretable)

Top standardized coefficients: `log_return_1d`, `momentum_10d`, `market_id_MSFT`, `market_id_NVDA`, `rolling_return_5d`. The `market_id` dummy coefficients being prominent is expected and not itself informative about markets in general — it mostly reflects that MSFT's realized 5-day-positive rate (28.4%, see `TARGET.md`) differs enough from the pooled-universe average that the model uses "is this MSFT" as a per-asset base-rate adjustment, distinct from the market-wide momentum/return signals.

## Verification

- `tests/test_explain.py` — 7 offline tests, including a synthetic-signal recovery test: a feature deliberately constructed to determine `y` is confirmed to rank at or near the top by both tree importance and permutation importance, proving the methods actually detect real signal rather than returning arbitrary orderings.
- Live run against the real Stage 9 models produced all 4 models' importance rankings, cross-model agreement table, and SHAP values for 2 of 4 models (HGB skipped per the `shap` library limitation above, not hidden).

## Stage 10 Completion Check

- [x] Feature importance for tree models (Random Forest, XGBoost)
- [x] Permutation importance (all four models, model-agnostic)
- [x] SHAP where practical (2 of 4 models; the gap documented, not hidden)
- [x] Logistic Regression coefficient analysis
- [x] Cross-model comparison of predictive signal
- [x] Predictive vs. causal importance explicitly distinguished throughout

**Stage 10 status: COMPLETE.**
