# UNIVERSE.md — Market Universe and Theme Taxonomy

Defines which instruments the platform tracks and how they are grouped. Source tables live in `data/reference/`; `src/ingestion/universe.py` turns them into `dim_market`, the single list that ingestion, features, analytics and the web app all read. Nothing downstream hard-codes a ticker list.

## 1. Categories

Every instrument appears in one or more top-level categories, which are the filters used throughout the web app:

| Category | What it holds | Where it comes from |
|---|---|---|
| **Stocks** | every listed company (58) | `companies.csv`, `is_public = true` |
| **AI Supply Chain** | chips, hyperscalers, neoclouds, data centres, power, networking | `themes.csv` |
| **Energy** | nuclear and uranium, clean energy, storage, power generation, oil and gas, plus thematic ETFs | `themes.csv` |
| **Benchmarks** | S&P 500, Nasdaq-100, Vanguard FTSE All-World, Vanguard FTSE Emerging Markets, iShares Semiconductor | `funds.csv`, `role = benchmark` |
| **Crypto** | the current top 10 cryptocurrencies by market cap, plus pinned coins | `crypto_assets.csv` (generated) |

Two further themes, **AI Models** (frontier labs, including private ones) and **AI Applications** (enterprise software and consumer platforms), are used by the company explorer.

A company in a theme is always a priced market entity too: Constellation Energy is in Stocks, AI Supply Chain (Power) and Energy (Nuclear & Uranium) at once, and every theme page links each member to its price history.

## 2. Reference tables

| File | Grain | Notes |
|---|---|---|
| `companies.csv` | one row per company, public or private | `ticker` empty for private labs (OpenAI, Anthropic, xAI, …); `currency` is KRW for the two KRX listings |
| `funds.csv` | one row per ETF or index | `symbol` is the Yahoo symbol (`^GSPC`, `VWRL.L`); `ticker` is the market_id; `role` is `benchmark` or `thematic` |
| `themes.csv` | one row per (entity, theme, segment) | `entity_id` is a `company_id` or `fund_id`; `subsegment` refines e.g. Semiconductors into Compute / Memory & Storage / Foundry / Equipment; segments are listed upstream to downstream, which is the order the web app shows them in |
| `crypto_candidates.csv` | one row per candidate coin | the pool the top 10 is ranked from; `pinned` coins are always tracked |
| `crypto_assets.csv` | one row per tracked coin | **generated** by `src.ingestion.crypto_universe`; do not edit by hand |
| `events.csv` | one row per curated AI event | see `EVENT_STUDY.md` |

`themes.csv` replaces the earlier `company_ai_categories.csv`. It is the same many-to-many bridge, extended to funds and to non-AI themes.

## 3. AI Supply Chain

| Segment | Members |
|---|---|
| Semiconductors | NVIDIA, AMD, Intel, Arm, Broadcom, Marvell, TSMC, ASML, Applied Materials, Lam Research, KLA, Micron, SK Hynix, Samsung, SanDisk |
| Hyperscalers | Microsoft, Amazon, Alphabet, Meta, Oracle, Alibaba |
| Neoclouds | CoreWeave, Nebius, IREN |
| Data Centres | IREN, TeraWulf, Cipher Digital, Applied Digital, Equinix, Digital Realty, Super Micro |
| Power | Vertiv, Eaton, GE Vernova, Constellation Energy, Vistra, Bloom Energy |
| Networking | Broadcom, Marvell, Arista, Cisco, Credo, Coherent |

ServiceNow and IBM sit under AI Applications (enterprise AI software) rather than being labelled as infrastructure.

## 4. Energy

| Segment | Members |
|---|---|
| Nuclear & Uranium | Constellation Energy, Oklo, NuScale, Cameco, Centrus, WisdomTree Uranium and Nuclear Energy ETF (NCLR) |
| Clean Energy | NextEra, First Solar, iShares Global Clean Energy Transition ETF (INRG) |
| Energy Storage | Amprius (AMPX), Eos Energy, Fluence |
| Power Generation | Vistra, GE Vernova, Bloom Energy |
| Oil & Gas | ExxonMobil, Chevron, Shell, iShares MSCI World Energy Sector ETF (WENS) |

"CED" from the original request has no Yahoo Finance listing on the US, London or ASX exchanges; Constellation Energy (**CEG**) was taken as the intended ticker.

## 5. Listing choices for funds

- **NCLR** — `NCLR.L`, the USD line. The GBP line `NCLP.L` has broken Yahoo data (a 78× jump in March 2025).
- **INRG** — `INRG.MI` (Milan, EUR). Yahoo's London series `INRG.L` has a block of stale, zero-volume rows at the wrong price level from late April to May 2025, which shows up as a false +33% day.
- **WENS** — `WENS.L` (GBP).
- **VWRL / VFEM** — the distributing London lines `VWRL.L` / `VFEM.L` (GBP).
- **Nasdaq-100** — `^NDX` replaces the Nasdaq Composite (`^IXIC`) used earlier.

Prices are stored in each instrument's own currency (the web app labels non-USD prices). Returns, volatility and drawdowns are currency-neutral within a series; cross-currency comparisons of *levels* are not meaningful.

## 6. Dynamic crypto top 10

`python -m src.ingestion.crypto_universe` (also run at the start of every `run_ingestion`, unless `--no-crypto-refresh`):

1. Ranks coins by market cap from CoinCodex's full listing. When that endpoint is down, it falls back to CoinCodex's per-coin history endpoint for every coin in `crypto_candidates.csv`. The pool is roughly 3× larger than the top 10 and only has to *contain* the top 10. When this was written the listing was returning Cloudflare 5xx errors, so the fallback was in use.
2. Keeps the top 10, plus the pinned coins (BTC, ETH and SOL, which the models are trained on).
3. Checks each coin's Yahoo symbol (`SYMBOL-USD`) and uses it only if Yahoo's latest close is within 5% of CoinCodex's price. Yahoo reuses tickers for unrelated coins (`TON-USD` trades near $0.005), so a coin without a trusted Yahoo symbol is priced from CoinCodex instead.
4. If CoinCodex is unreachable entirely, the existing `crypto_assets.csv` is kept.

A coin that drops out of the top 10 keeps its price file on disk, but the API only serves instruments in the current universe.

## 7. Data quality notes

- Yahoo occasionally returns a row whose close sits just outside that day's high/low (KRX listings, thin London ETF lines, and crypto's still-forming current-day candle). The Yahoo adapter widens high/low to contain open and close and logs how many rows it changed, rather than dropping the whole asset at validation.
- Private labs have no price series, so AI events for xAI or Mistral are shown on the timeline but not measured in the event study.
