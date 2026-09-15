# FEATURES.md — Feature Dictionary (Stage 6)

Every feature is computed by `src/features/{market_features,sentiment_features,cross_sectional_features}.py` and combined by `src/features/pipeline.py`. Leakage-safety contract: **a feature value at row t is a function of rows ≤ t only** — enforced by using pandas `.shift()`/right-aligned `.rolling()` exclusively (never `center=True`), and proven by `tests/test_features.py::TestLeakageSafety::test_market_features_unaffected_by_future_mutation`, which mutates all data after a cutoff and asserts every feature column before the cutoff is byte-identical.

## Market Features (`market_features.py`)

| Feature | Definition | Window |
|---|---|---|
| `return_1d`, `log_return_1d` | 1-day simple/log return | — |
| `rolling_vol_7d`, `rolling_vol_30d` | rolling std of `log_return_1d` | 7d, 30d |
| `drawdown` | price / running-max price − 1 | expanding |
| `lag_return_{1,3,5,10}d` | `return_1d` shifted back N days | — |
| `rolling_return_{5,10,30}d` | price(t)/price(t−N) − 1 | 5d, 10d, 30d |
| `sma_{10,30,50}d` | simple moving average of close | 10d, 30d, 50d |
| `momentum_{10,30}d` | price(t)/SMA_N(t) − 1 | 10d, 30d |
| `rsi_14d` | classic RSI (rolling-mean gains/losses, not Wilder-smoothed) | 14d |
| `volume_change_1d` | 1-day % change in volume | — |
| `volume_ratio_10d` | volume(t)/rolling-mean-volume(t) − 1 | 10d |

## Sentiment Features (`sentiment_features.py`)

| Feature | Definition |
|---|---|
| `sentiment_current` | mean VADER compound score of that entity's headlines on date t |
| `lag_sentiment_{1,3,5}d` | `sentiment_current` shifted back N days |
| `rolling_mean_sentiment_7d` | 7-day rolling mean of `sentiment_current`, skipping no-news days |
| `sentiment_volatility` | std of same-day sentiment scores (when >1 article that day) |
| `positive_ratio`, `negative_ratio` | share of that day's articles scoring >0.2 / <−0.2 |
| `news_volume` | count of matched articles that day (0 on no-news days — a real fact, not missing data) |

**No-news-day convention:** `news_volume = 0` (a fact) but `sentiment_current` and friends stay `NaN` (undefined) — a day with zero coverage is not evidence of neutral sentiment, so it is never filled with a fabricated 0. See `tests/test_features.py::TestSentimentFeatures::test_no_news_days_get_zero_volume_not_fabricated_sentiment`.

**Current data reality:** with the key-free Google News RSS source (Stage 3/4), coverage is sparse relative to a multi-year price backfill — in the live Stage 6 run, `sentiment_current` is non-null for well under 1% of MSFT's trading days. This is expected and documented, not a bug; see `CHECKPOINT.md` Stage 5's note on the same underlying limitation.

## Cross-Sectional Features (`cross_sectional_features.py`)

| Feature | Definition |
|---|---|
| `market_return` | equal-weighted mean `return_1d` across every ingested asset that day (crypto + equity) |
| `ai_index_return` | equal-weighted mean `return_1d` across ingested **equity** assets only |
| `sector_return` | equal-weighted mean `return_1d` across equities sharing the asset's `ai_category` (from `company_ai_categories.csv`) |
| `relative_performance` | `return_1d − market_return` |
| `relative_sector_performance` | `return_1d − sector_return` |

These use same-day cross-sectional data, which is contemporaneous (available at t), not future, information — leakage-safe under the same rule as single-asset features. **Caveat:** with the current small ingested universe (6 assets), each asset is a non-trivial share of its own benchmark (e.g. MSFT is 1/6 of `market_return`, and TSM/MSFT/NVDA are each 1/3 of `sector_return` if uniquely categorized) — a known small-sample artifact of equal-weighted, include-self benchmarking, not a bug. Revisit (e.g. leave-one-out weighting) once the tracked universe grows materially.

## Explicitly Deferred: AI Event Features

The target spec's feature list includes model-release indicators, major-announcement indicators, benchmark-improvement signals, and company-event indicators. **These are not implemented in Stage 6** — no event data source exists yet (`fact_model_release` / `fact_company_event` from `DATA_MODEL.md` were never populated; Stage 3 ingestion only covers market prices and general news headlines, not structured event data). Rather than add zero-filled placeholder columns that would look like real features without being one, this category is left out entirely and tracked as explicit prerequisite work for Stage 11 (Event Study), which needs the same event data anyway.

## Stage 6 Completion Check

- [x] Reusable feature-engineering pipeline (`src/features/`)
- [x] Market features: lagged/rolling returns, rolling volatility, moving averages, momentum, RSI, volume changes, drawdown
- [x] Sentiment features: current/lagged/rolling sentiment, sentiment volatility, positive/negative ratio, news volume
- [x] Cross-sectional features: sector return, market return, relative performance, AI-index return
- [ ] AI event features — explicitly deferred (see above), not a silent gap
- [x] Every feature has a clearly defined timestamp (`date` column, one row per (`market_id`, `date`))
- [x] Leakage-safety proven by regression test, not just asserted

**Stage 6 status: COMPLETE** (AI event feature category explicitly out of scope per above).
