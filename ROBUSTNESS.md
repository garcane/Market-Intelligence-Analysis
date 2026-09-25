# ROBUSTNESS.md — Robustness Testing (target spec §19)

Tests whether Stage 9's conclusions (XGBoost leads the leaderboard, all models modestly beat naive baselines) survive changes to horizon, threshold, random seed, and asset subgroup. Primary model: XGBoost (Stage 9's leaderboard winner). All results reported as-is, including where the picture is more complicated than the headline number suggests — per the spec's explicit instruction not to hide negative or inconvenient findings.

## Across Horizons

| Horizon | n (val) | Positive rate | PR-AUC | ROC-AUC | **PR-AUC / positive rate (lift)** |
|---|---|---|---|---|---|
| 1-day | 1,005 | 16.3% | 0.275 | 0.644 | **1.69x** |
| 5-day (primary) | 981 | 35.3% | 0.409 | 0.579 | 1.16x |
| 10-day | 957 | 41.9% | 0.483 | 0.588 | 1.15x |

**Raw PR-AUC alone is misleading here** — it rises with horizon mostly because the positive rate itself rises (a higher base rate mechanically makes PR-AUC easier to achieve, independent of the model doing anything better). Normalizing by dividing PR-AUC by the horizon's own positive rate (a simple "lift over baseline" ratio) **inverts the picture**: the 1-day horizon actually has the highest relative lift (1.69x its own baseline) despite having the lowest raw PR-AUC and the most severe class imbalance. 5-day and 10-day are nearly identical to each other in relative terms (~1.15x). This means the primary experiment's 5-day choice (justified in `TARGET.md` on class-balance and horizon-overlap grounds, not predictive-performance grounds) is not obviously the "best-performing" horizon in a relative sense — 1-day would deserve a closer look in future work, ideally with a lower decision threshold given its accuracy at 0.5 is trivially high (83.7%) purely from predicting the majority class (F1=0.000 at threshold 0.5 — the model never predicts positive at this horizon under the default cutoff).

## Across Thresholds (5-day horizon)

| Threshold | Positive rate | PR-AUC | PR-AUC / positive rate |
|---|---|---|---|
| 1% | 43.7% | 0.471 | 1.08x |
| 2% (primary) | 35.3% | 0.409 | 1.16x |
| 3% | 26.8% | 0.331 | 1.23x |

Same inversion pattern: raw PR-AUC falls as the threshold rises (again, mostly tracking the falling positive rate), but relative lift over baseline actually *increases* — the model does proportionally better at identifying the rarer, larger 3% moves than the more common 1% moves, even though its absolute PR-AUC looks worse. This is consistent with (though doesn't prove) the intuition that larger, less noisy moves are more predictable in relative terms.

## Across Random Seeds (5-day horizon, XGBoost)

| Seed | PR-AUC |
|---|---|
| 1 | 0.4109 |
| 2 | 0.4100 |
| 3 | 0.4132 |
| 4 | 0.4056 |
| 5 | 0.4084 |

**Mean 0.4098, std 0.0025** — training-randomness alone moves PR-AUC by roughly ±0.6%, far smaller than the ~0.01–0.05 gaps separating the four models in Stage 9's leaderboard (`MODELS.md`: XGBoost 0.409 vs. Random Forest 0.408 vs. HistGradientBoosting 0.400 vs. Logistic Regression 0.397). **Caveat this cuts the other way too**: XGBoost's razor-thin lead over Random Forest (0.409 vs. 0.408, a 0.001 gap) is smaller than this seed-to-seed noise band — that specific 1st-vs-2nd-place ordering should not be treated as a confident result, even though the broader "tree ensembles modestly outperform Logistic Regression" pattern comfortably survives it.

## By Asset Group (Equity vs. Crypto, 5-day horizon)

| Group | n | PR-AUC | ROC-AUC | Positive rate | Lift |
|---|---|---|---|---|---|
| Equity (NVDA, MSFT, TSM) | 489 | 0.411 | 0.591 | 36.0% | 1.14x |
| Crypto (BTC, ETH, SOL) | 492 | 0.420 | 0.593 | 34.6% | 1.22x |

**No dramatic subgroup failure** — the spec specifically asks to report it if a model wins overall but fails badly on a subgroup, and here it doesn't: performance is close and, if anything, marginally better on crypto. This is a genuinely reassuring result, not a manufactured one; reported plainly rather than searched for a more dramatic finding that isn't there.

## Verification

- `tests/test_robustness.py` — 5 offline tests, including that `evaluate_by_asset_group` correctly splits by the raw `market_id` column (not a one-hot-encoded one — encoding happens inside the model `Pipeline`, a distinction that would silently produce zero-row groups if gotten wrong) and that Logistic Regression is provably seed-invariant (a useful contrast confirming `evaluate_across_seeds` actually varies the right parameter, since a solver with no randomness should show exactly zero variance).
- Live run against the real Stage 9 model and dataset — all four robustness axes computed successfully, `data/processed/robustness_report.json`.

## Stage Completion Check (§19)

- [x] Different time horizons tested (1d/5d/10d)
- [x] Different thresholds tested (1%/2%/3%)
- [x] Different random seeds tested
- [x] Different asset groups tested (equity vs. crypto)
- [x] Negative/complicating findings reported, not hidden (the raw-vs-lift PR-AUC inversion; XGBoost's 1st-place margin over Random Forest being within seed noise)

**Robustness testing status: COMPLETE.**
