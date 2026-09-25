# ABLATION_STUDY.md — Feature Group Ablation (target spec §20)

**Central question**: does adding AI/news sentiment actually improve predictive performance? Four experiments, same architecture (XGBoost, Stage 9's leaderboard winner) and same horizon (5-day) each time — only the feature set changes.

Experiment D substitutes "Market + Sentiment + Cross-sectional" for the spec's literal "Market + Sentiment + AI event features" — AI event features were never built (`FEATURES.md`'s Stage 6 deferral: no event data source exists, and fabricating placeholder columns was explicitly rejected at the time). Cross-sectional features (market/sector/AI-index return — all real, already built in Stage 6) keep the experiment's actual point intact: does the "everything beyond raw market data" feature group help.

## Results

| Experiment | # Features | PR-AUC | ROC-AUC | F1 |
|---|---|---|---|---|
| **A — Market only** | 17 | 0.404 | 0.570 | 0.188 |
| **B — Sentiment only** | 9 | 0.385 | 0.564 | **0.000** |
| **C — Market + Sentiment** | 26 | **0.397** | 0.570 | 0.185 |
| **D — Market + Sentiment + Cross-sectional** | 31 | 0.406 | 0.576 | 0.197 |

## Answer: No, Sentiment Does Not Currently Improve Performance — and Sometimes Slightly Hurts It

This is the honest result, not a spun one:

- **Experiment B (sentiment-only) has F1 = 0.000** — the model never predicts a positive class at the default threshold using sentiment features alone. Unsurprising given `FEATURES.md`'s documented finding that `sentiment_current` is non-null for well under 1% of rows in the current data — a feature set that's ~99% a constant 0 (the sparse-feature imputation value) plus a `_missing` flag carries very little standalone predictive signal.
- **Experiment C (market + sentiment) scores *lower* PR-AUC than Experiment A (market only)** — 0.397 vs. 0.404. Adding sentiment features to the market feature set did not help, and by this measure very slightly hurt (likely because the extra near-constant/sparse columns add noise/complexity for the tree splitter without adding real signal, rather than because sentiment is actively harmful in a meaningful sense).
- **Experiment D (adding cross-sectional features on top) is the best of the four (0.406)** — but only marginally better than market-only (A, 0.404), and the improvement is attributable to the cross-sectional features (`ai_index_return`, `market_return`), not sentiment — consistent with `EXPLAINABILITY.md`'s finding that `ai_index_return` is a top-10 permutation-importance feature for all four Stage 9 models, while no sentiment feature appears in any model's top 10.

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
