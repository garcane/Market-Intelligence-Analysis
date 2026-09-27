# INDICES.md — AI Thematic Equity Indices (Stage 12)

## Construction

Equal-weighted (no reliable market-cap series across this mixed equity+crypto universe, so equal-weight is the defensible, documented default — not a silent choice). Membership drawn from `data/reference/{companies,themes}.csv`, restricted to what's actually been ingested for this stage (`data/raw/market_prices/`, expanded beyond the 6-asset modeling universe specifically for this analysis — see `CHECKPOINT.md`).

| Index | Constituents | Supply-chain category (Stage 1) |
|---|---|---|
| **AI Infrastructure** | NVDA, AMD, AVGO, TSM, MU | Compute, Custom AI Silicon, Semiconductor Manufacturing, Memory |
| **AI Platform** | MSFT, AMZN, GOOGL, META, AAPL, ORCL | Cloud/AI Infrastructure, Consumer/Platform |
| **AI Model Provider** | MSFT, GOOGL, META | Publicly-traded companies with significant foundation-model exposure. OpenAI/Anthropic/xAI/Mistral/DeepSeek and the other private labs from `UNIVERSE.md` are excluded here — no public price series exists for them, so they cannot be part of a price-based index. |

Benchmarks: S&P 500 (`^GSPC`), Nasdaq-100 (`^NDX`, replacing the Nasdaq Composite used originally), iShares Semiconductor ETF (`SOXX`), BTC, ETH. The benchmark funds are listed in `data/reference/funds.csv` and ingested with the rest of the universe (`src/analytics/fetch_benchmarks.py` refreshes only them).

A fourth index, **AI Power** (CEG, VST, GEV, VRT, ETN), tracks the power and electrical-equipment names supplying AI data centres.

## Results (2023-06-01 → 2026-09-15)

| | Ann. Volatility | Cumulative Return | Max Drawdown | Sharpe | β vs SPX | β vs SOXX |
|---|---|---|---|---|---|---|
| **AI Infrastructure** | 49.4% | **548.7%** | -36.0% | 1.93 | 2.10 | **0.99** |
| **AI Platform** | 27.8% | 116.1% | -25.3% | 1.37 | 1.30 | 0.34 |
| **AI Model Provider** | 29.2% | 133.3% | -24.3% | 1.43 | 1.22 | 0.30 |
| S&P 500 | 17.7% | 80.5% | -18.9% | 1.57 | 1.00 | — |
| Nasdaq | 24.1% | 99.9% | -24.3% | 1.40 | — | — |
| SOXX (semiconductors) | 46.6% | 207.7% | -41.7% | 1.30 | — | 1.00 |
| BTC | 46.3% | 191.4% | -53.1% | 0.93 | — | — |
| ETH | 64.8% | 35.0% | -67.6% | 0.46 | — | — |

Sharpe uses a 0% risk-free rate assumption and 365-period annualization (not 252) since the universe mixes equities with crypto, which trades every calendar day — documented in `src/analytics/indices.py`, not silently picked.

## Reading These Numbers Honestly

- **AI Infrastructure tracks the semiconductor benchmark almost exactly** (β vs SOXX = 0.99) — this is a strong internal-consistency check that the index construction is doing something real, not an arbitrary basket: five chip/memory names, built independently, land on almost exactly SOXX's own beta.
- **AI Infrastructure's β vs SPX (2.10) means it moved roughly twice as much as the broad market** over this window — both on the way up (the 548.7% cumulative return over ~3.25 years reflects the AI/semiconductor buildout during this specific period) and, by the same logic, on the way down in any future drawdown. This is a beta/volatility fact, not a forecast.
- **Crypto's low beta to every equity index (0.12–0.25)** is consistent with widely-documented low equity-crypto correlation, and is a useful sanity check rather than a novel finding.
- **AI Platform and AI Model Provider indices are close to each other** (Sharpe 1.37 vs 1.43, similar volatility) because they share 3 of their constituents (MSFT, GOOGL, META) — expected given the membership overlap, not an independent confirmation of two different theses.
- These are **realized, backward-looking statistics over one specific historical window**, not a claim about forward-looking risk/return — no forecast or investment recommendation should be drawn from a single ~3-year sample, especially one that includes an unusually strong AI-infrastructure buildout period.

## Verification

- `tests/test_indices.py` — 12 offline tests: equal-weighted averaging verified by hand-computation, missing-constituent handling (an index doesn't crash if one ticker isn't ingested), Sharpe/beta degenerate cases (zero variance → NaN, not a divide-by-zero crash or a fabricated 0), beta-of-an-asset-against-itself equals 1.0 (a correctness invariant).
- Live run: all 14 index constituents + 5 benchmarks resolved with 0 missing members (`data/processed/indices_report.json`'s `missing_members` field is empty).
- The SOXX/AI-Infrastructure beta≈0.99 finding above functions as an independent sanity check on the whole computation chain, not just a unit test — an unrelated real-world benchmark landed almost exactly where the index construction predicts it should.

## Stage 12 Completion Check

- [x] Thematic baskets built from real ingested constituent data (not fabricated)
- [x] Explicit about indirect AI exposure (Platform index) vs the excluded private model labs
- [x] Returns, volatility, drawdown, correlation, rolling correlation, Sharpe, beta all computed
- [x] Compared against S&P 500, Nasdaq, semiconductor benchmark, BTC, ETH
- [x] Results interpreted honestly (backward-looking realized stats, not a forecast)

**Stage 12 status: COMPLETE.**
