# ABLATION_STUDY.md — Feature Group Ablation (target spec §20)

**Central question**: does adding AI/news sentiment actually improve predictive performance? Four experiments, same architecture (XGBoost, Stage 9's leaderboard winner) and same horizon (5-day) each time — only the feature set changes.

Experiment D substitutes "Market + Sentiment + Cross-sectional" for the spec's literal "Market + Sentiment + AI event features" — AI event features were never built (`FEATURES.md`'s Stage 6 deferral: no event data source exists, and fabricating placeholder columns was explicitly rejected at the time). Cross-sectional features (market/sector/AI-index return — all real, already built in Stage 6) keep the experiment's actual point intact: does the "everything beyond raw market data" feature group help.

## Results

Two independent runs are shown: the working environment, and a fresh `git clone` reproduction (fresh install, fresh live ingestion; see `REPRODUCIBILITY.md`).

| Experiment | # Features | PR-AUC (working env) | PR-AUC (git clone) | F1 (working / clone) |
|---|---|---|---|---|
| **A — Market only** | 17 | 0.404 | 0.400 | 0.188 / 0.161 |
| **B — Sentiment only** | 9 | 0.385 | 0.385 | **0.000 / 0.000** |
| **C — Market + Sentiment** | 26 | 0.397 | 0.401 | 0.185 / 0.176 |
| **D — Market + Sentiment + Cross-sectional** | 31 | 0.406 | 0.409 | 0.197 / 0.176 |

For scale: XGBoost's PR-AUC varies by a standard deviation of 0.0025–0.0039 across random seeds alone (`ROBUSTNESS.md`).

## Answer: No, Sentiment Does Not Measurably Change Performance

- **Experiment B (sentiment-only) has F1 = 0.000 in both runs**: the model never predicts a positive class at the default threshold using sentiment features alone. Unsurprising given `FEATURES.md`'s documented finding that `sentiment_current` is non-null for well under 1% of rows — a feature set that's ~99% a constant 0 (the sparse-feature imputation value) plus a `_missing` flag carries very little standalone predictive signal.
- **Adding sentiment to market features (C vs. A) has no measurable effect.** The gap is -0.007 in one run and +0.001 in the other: its sign flips between runs and both values sit inside seed noise. *Correction:* an earlier version of this document, the README and `ANALYSIS_REPORT.md` said sentiment "slightly hurts" performance, based on the first run alone. The reproduction run showed that claim was not supported.
- **Experiment D (adding cross-sectional features) scores highest in both runs** (0.406, 0.409), ahead of market-only by 0.002 and 0.009. The direction is consistent, but the smaller gap is within seed noise, so treat it as weak evidence. It is consistent with `EXPLAINABILITY.md`, where `ai_index_return` is a top-10 permutation-importance feature for all four Stage 9 models and no sentiment feature appears in any model's top 10.

**This is a real, useful finding, not a failure of the sentiment pipeline's correctness** — Stage 4's dual-model sentiment scoring is independently verified working correctly (`CHECKPOINT.md`'s Stage 4 entry: real VADER/TextBlob disagreement measured and documented). The issue is coverage, not correctness: with the key-free Google News RSS source's no-historical-archive limitation (documented repeatedly since Stage 5's EDA), sentiment simply doesn't have enough matched rows yet to carry predictive weight in a pooled model. **The honest conclusion is conditional**: sentiment may still be predictive in principle, but this dataset cannot currently support testing that claim with any statistical confidence, given how sparse the coverage is. A meaningful re-test of this ablation would need either a historical news source (the Marketaux adapter, enabled by `MARKETAUX_API_TOKEN`, exists but does not yet request date ranges, so it would need that added before it could backfill) or a much longer live-collection window before sentiment coverage density approaches what would be needed to move a pooled classifier.

## Verification

- `tests/test_ablation.py` — 5 offline tests: the four experiments' feature sets nest correctly (A, B ⊂ C ⊂ D), market-only and sentiment-only are properly disjoint, and every experiment produces valid bounded metrics on synthetic data.
- Live run against the real Stage 6–9 pipeline (`data/processed/ablation_report.json`) — the F1=0.000 result for sentiment-only was specifically re-verified (not treated as a bug) against `FEATURES.md`'s independently-documented ~1% sentiment coverage figure, which fully explains it.

## Stage Completion Check (§20)

- [x] Experiment A: market features only
- [x] Experiment B: sentiment features only
- [x] Experiment C: market + sentiment
- [x] Experiment D: market + sentiment + cross-sectional (substituting for AI-event features, which don't exist — documented, not silently swapped)
- [x] The central question ("does sentiment help?") answered directly: **no, not with the current data's sentiment coverage** — and the reason why is explained, not just the result

**Ablation study status: COMPLETE.**
