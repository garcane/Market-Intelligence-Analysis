# UNIVERSE.md — AI & Financial Market Taxonomy (Stage 1)

Defines the structured universe of entities the platform tracks. Source tables live in `data/reference/`.

## 1. Design Decisions

- **One row per legal entity, many category tags** — a company like Microsoft is simultaneously an AI model provider (Azure OpenAI, Copilot), cloud infrastructure provider (Azure), and consumer platform (Windows/Office). Rather than duplicating the company row per category (which the target spec warns against — "avoid duplicate entities where possible"), `companies.csv` holds one canonical row per entity and `company_ai_categories.csv` is a many-to-many bridge table assigning one or more `ai_category` values to each `company_id`. This is the standard star-schema pattern for a many-to-many dimension attribute and will become `dim_company` + a bridge table in `DATA_MODEL.md` (Stage 2).
- **Private labs included, `ticker` left null** — OpenAI, Anthropic, xAI, Mistral, DeepSeek, Moonshot, Zhipu, and MiniMax are not publicly traded. They are still first-class rows in `companies.csv` (`is_public=false`, `ticker` empty) because Stage 11 (event study) needs to record model-release events for them even without price data to react against directly — their releases still move the equities of partners/competitors (e.g., a DeepSeek release moving NVIDIA).
- **Crypto kept as its own asset universe, not forced into `companies.csv`** — cryptocurrencies are not equities and have no ticker/exchange/company structure, so they get a separate `crypto_assets.csv`. This preserves the project's original SUI/XRP/ETH work while keeping the equity and crypto universes cleanly separable in the data model (`dim_market` will need an `asset_type` discriminator: `equity` vs `crypto`).
- **List is explicitly extensible, not authoritative** — per the target prompt ("Do not assume this list is permanently correct"), new rows can be appended to any of the three CSVs without touching pipeline code, since Stage 3 ingestion will key off `company_id`/`ticker`/`asset_id`, not hard-coded lists.

## 2. AI Model Provider Universe (`companies.csv` filtered to `ai_category = 'AI Model Provider'` in the bridge table)

| Region | Entities |
|---|---|
| US / Western | OpenAI, Anthropic, Alphabet (Google DeepMind), xAI, Meta, Microsoft, Mistral AI |
| Chinese | DeepSeek, Alibaba (Qwen), Moonshot AI (Kimi), Zhipu AI (GLM), Baidu (Ernie), Tencent (Hunyuan), MiniMax |

## 3. AI Equity Universe, by supply-chain position

| Category | Companies |
|---|---|
| Compute | NVIDIA, AMD, Intel |
| Custom AI Silicon / Networking | Broadcom, Marvell, Arista Networks |
| Semiconductor Manufacturing | TSMC, ASML, Applied Materials, Lam Research |
| Memory | Micron, SK Hynix, Samsung, SanDisk |
| Cloud / AI Infrastructure | Microsoft, Alphabet, Amazon, Oracle, Meta, CoreWeave, Nebius |
| Consumer / Platform | Apple, Microsoft, Alphabet, Amazon, Meta |

33 unique public + private companies, 45 category assignments (see `company_ai_categories.csv` for the full role-level breakdown, including the reasoning for each cross-category tag).

## 4. Crypto Asset Universe

BTC, ETH, SOL, XRP, BNB, ADA, DOGE, TRX, LINK, AVAX — see `crypto_assets.csv`. BTC/ETH serve as market-beta benchmarks (per Stage 12's request to compare AI indices against BTC/ETH); XRP is the asset the existing repo's sentiment notebook already partially targets. SUI has been deliberately excluded from the tracked universe (confirmed decision, despite the repo holding a legacy SUI OHLCV CSV from the original project) — `sui_2023-05-09_2025-02-08.csv` is retained as a historical reference file only, not a Stage 3 ingestion target.

## 5. Known Gaps / Deferred

- No `dim_model` (individual model releases, e.g. "GPT-5", "Gemini 3", "DeepSeek-V4") yet — that belongs to Stage 2's data model design, seeded from this company universe.
- Samsung and SK Hynix trade in KRW on KRX; a currency-normalisation decision is deferred to Stage 3 ingestion design rather than baked into this taxonomy.
- Not all listed companies necessarily have easily obtainable free-tier price history (e.g. Korean exchange tickers via yfinance) — this will be validated, not assumed, during Stage 3 ingestion, and any that fail will be documented rather than silently dropped.

## 6. Stage 1 Completion Check

- [x] AI model provider taxonomy created, extensible (§2)
- [x] AI equity universe grouped by supply-chain category (§3)
- [x] Canonical company table with required fields (`company_id, company_name, ticker, country, region, industry, ai_category*, exchange, active_from, active_to`) — `ai_category` implemented as a bridge table rather than a single column, documented above with rationale
- [x] Duplicate entities avoided (one row per company; multi-category via bridge table)
- [x] Crypto asset universe defined for the existing SUI/XRP/ETH work

**Stage 1 status: COMPLETE.**
