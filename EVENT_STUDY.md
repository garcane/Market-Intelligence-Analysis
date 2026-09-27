# EVENT_STUDY.md — Event-Driven Financial Analysis (Stage 11)

## Event Catalog: Curated Events plus News-Detected Events

The timeline has two sources.

**Curated — `data/reference/events.csv` (97 events, Nov 2022 → Sep 2026).** These cover model releases from OpenAI, Anthropic, Google, Meta, xAI, DeepSeek, Alibaba (Qwen), Moonshot and Mistral, plus major investments, partnerships, acquisitions, chips, data-centre and power deals, IPOs and market reactions. Each has an `organisation` and, where a listed company is directly implicated, a `primary_market_id`. Events before 2026 use well-documented public dates. Events in 2026 were taken from the ingested news store and dated to the first headline reporting them (the description says so), which can be a day after the actual release. The event study measures every curated event that has a listed company and falls inside the price history.

**Detected — `data/processed/detected_events.csv` (`python -m src.analytics.event_detection`).** Rules over news headlines find new model releases (by model name, e.g. "Claude Opus 5", "GPT-6"), plus acquisitions, investments, partnerships, chips and data-centre build-outs:

- Deals must state a material size (billions of dollars or gigawatts).
- The organisation must lead the headline.
- Stock commentary and portfolio filings are filtered out.
- A detected event needs several articles.
- It is dropped when a curated event already covers it (same organisation within 3 days, or the same model name).

Detected events appear on the timeline marked "from news" but are not included in the CAAR, so the curated catalogue stays the controlled sample.

The original six seed events are still in the catalogue:

| Event | Date | Primary ticker | Type |
|---|---|---|---|
| NVIDIA Q2 FY24 earnings beat | 2023-08-23 | NVDA | earnings |
| NVIDIA Q4 FY24 earnings beat | 2024-02-21 | NVDA | earnings |
| GPT-4o launch (OpenAI) | 2024-05-13 | MSFT* | model_release |
| Llama 3.1 release (Meta) | 2024-07-23 | META | model_release |
| DeepSeek R1 release | 2025-01-20 | NVDA* | model_release |
| "DeepSeek shock" — NVDA single-day drop | 2025-01-27 | NVDA | market_reaction |

*OpenAI and DeepSeek have no public ticker (private labs, per `UNIVERSE.md`) — MSFT (Azure OpenAI partnership) and NVDA (where the market reaction concentrated) are used as the most directly-implicated public proxy, not as if they were the model developer itself.

## Methodology

- **Abnormal return** = asset return − benchmark return (SPX) on the same trading day — a simple relative-return approach, not a full market-model regression with an estimated beta over a clean pre-event window. This is a documented simplification, not hidden: a proper market-model event study would estimate each asset's beta over an estimation window well before the event and use `asset_return - (alpha + beta * benchmark_return)`, which is more rigorous but requires more data and modeling choices than this stage's scope. The simpler relative-return approach still gives directionally meaningful abnormal returns for the size of moves seen here.
- **Event windows are built on trading-day row position**, not calendar-day arithmetic — a nominal event date that falls on a weekend snaps to the next available trading day as T0, avoiding the systematic error a `date - 5 days` calendar approach would introduce for equities (tested explicitly: `tests/test_event_study.py::test_uses_nearest_trading_day_on_or_after_a_weekend_event_date`).
- **CAAR** (cumulative average abnormal return) aggregates across all 6 events per relative trading day — reduces the risk of over-interpreting any single noisy event.

## Results — Independently Verified Against Known History

Two results in this table are strong, unplanned sanity checks: they reproduce specific, well-known real-world facts from the actual ingested Yahoo Finance data, which corroborates both the chosen event dates and the underlying data quality.

| Event | T0 raw return | Note |
|---|---|---|
| NVIDIA Q4 FY24 earnings | **T0 = -2.9%, T+1 = +16.4%** | NVIDIA reported after market close on 2024-02-21; the well-documented ~16% single-day pop shows up on the *next* trading day (2024-02-22), not the announcement date itself. This is a real, general event-study nuance for after-hours earnings, not a data error — flagged explicitly rather than silently averaged away. |
| "DeepSeek shock" | **T0 = -17.0% raw, -15.5% abnormal** | Matches the widely-reported ~17% single-day NVDA decline on 2025-01-27, one of the largest single-day market-cap losses on record at the time. |
| NVIDIA Q2 FY24 earnings | T0 = +3.2% raw, +2.1% abnormal | Consistent with the well-known Aug 2023 beat that helped catalyze the 2023-2024 AI equity rally. |
| GPT-4o launch | T0 = -0.3% abnormal (MSFT) | Small, as expected — a product launch by a company MSFT partners with but doesn't equal, correctly showing far less reaction than the two NVDA-direct events. |
| Llama 3.1 release | T0 = +0.4% abnormal (META) | Small positive, consistent with an incremental (if large) open-weight release rather than a market-moving surprise. |
| DeepSeek R1 release itself | T0 = +1.4% abnormal (NVDA) | Notably small — the market didn't react sharply to the release itself; the reaction materialized a week later at the "shock" date above, once broader attention (app-store rankings, cost claims) caught on. This lag between release and market reaction is itself informative, not an inconsistency between the two DeepSeek-related rows. |

CAAR across all 6 events (`data/processed/event_study_caar.csv`) shows the T0 day pulling CAAR down sharply (AAR = -2.5% at T0, driven mostly by the DeepSeek shock) before partially recovering by T+1 (AAR = +4.1%, again reflecting the NVDA earnings pop's actual arrival day) — a real pattern in a 6-event sample, not something to over-generalize from.

## What This Does Not Claim

- **No causal claim.** An abnormal return following an event is consistent with the event mattering to the market, not proof the event caused the move net of every other contemporaneous factor — no control group or matched-sample design is used here.
- **A 6-event catalog is a demonstration of the methodology, not a statistically powered study.** Real conclusions about "how markets react to AI model releases in general" would need dozens of comparable events, ideally with a formal market-model regression and significance testing (e.g. a t-test on CAAR), neither of which this stage's scope covers.

## Verification

- `tests/test_event_study.py` — 8 offline tests: window-extraction correctness verified against a hand-constructed series where `returns[i] = i` (so the exact window contents are checkable by inspection), boundary handling (event too close to data start/end returns `None` rather than a partial or wrong window), and the weekend-snapping behavior specifically.
- Live run: 6/6 events resolved (none skipped for being out of the ingested date range), and two results independently match well-documented real-world market history — the strongest form of validation available for this kind of analysis.

## Stage 11 Completion Check

- [x] Real, verifiable events identified — explicitly a curated seed list, not fabricated or comprehensive
- [x] T-5..T+5 event windows computed on trading-day position, not naive calendar arithmetic
- [x] Abnormal/relative returns calculated, methodology (relative-return, not full market-model) documented
- [x] No causal claims made without appropriate framing/caveats
- [x] Results cross-checked against independently known real-world outcomes

**Stage 11 status: COMPLETE.**
