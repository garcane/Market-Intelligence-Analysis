# DATA_MODEL.md — Analytical Data Model (Stage 2)

Star-schema design: a small set of dimension tables plus grain-explicit fact tables. Every fact table's grain is stated explicitly to prevent silent fan-out during joins. Built directly on the Stage 1 universe (`UNIVERSE.md`, `data/reference/*.csv`).

## 1. Entity-Relationship Overview

```text
                         ┌───────────────┐
                         │   dim_date    │
                         └───────┬───────┘
                                 │ date
        ┌────────────────────────────────────────────────┐
        │                        │                        │
┌───────▼────────┐      ┌────────▼─────────┐    ┌─────────▼────────┐
│  fact_market_   │      │    fact_news     │    │ fact_company_    │
│    prices       │      │                  │    │    event         │
└───────┬────────┘      └────────┬─────────┘    └─────────┬────────┘
        │ market_id               │ news_id                │ company_id
┌───────▼────────┐      ┌────────▼─────────┐               │
│   dim_market    │      │  fact_sentiment  │               │
└───────┬────────┘      └────────┬─────────┘               │
        │ company_id/asset_id     │ news_id                 │
        │                         │ source_id                │
┌───────▼────────┐      ┌────────▼─────────┐               │
│  dim_company    │◄─────┤ dim_news_source  │               │
└───────┬────────┘      └──────────────────┘               │
        │ company_id                                        │
┌───────▼────────┐      ┌──────────────────┐    ┌───────────▼────────┐
│company_ai_      │      │    dim_model     │───►│ fact_model_release │
│ categories(bridge)│    └────────┬─────────┘    └─────────────────────┘
└────────────────┘               │ model_id
                        ┌────────▼─────────┐
                        │fact_model_        │
                        │  benchmark        │
                        └──────────────────┘

dim_sector is referenced by dim_company.industry / themes.segment (see §2.6) — kept as a lookup, not a heavy join target.
```

## 2. Dimension Tables

### 2.1 `dim_company`
Grain: one row per legal entity. Source: `data/reference/companies.csv`.

| Column | Type | Notes |
|---|---|---|
| `company_id` | text, PK | e.g. `nvidia`, `openai` |
| `company_name` | text | |
| `ticker` | text, nullable | null for private labs (OpenAI, Anthropic, DeepSeek, etc.) |
| `is_public` | bool | |
| `exchange` | text, nullable | |
| `country` | text (ISO2) | |
| `region` | text | |
| `industry` | text | free-text primary industry label |
| `active_from` | date | founding/IPO reference date |
| `active_to` | date, nullable | null = still active |

### 2.2 `themes` (bridge, many-to-many)
Grain: one row per (entity, theme, segment) assignment. Source: `data/reference/themes.csv` (replaces the earlier `company_ai_categories.csv`; see `UNIVERSE.md`).

| Column | Type | Notes |
|---|---|---|
| `entity_id` | text | FK → `dim_company.company_id` or a `fund_id` in `data/reference/funds.csv` |
| `theme` | text | AI Supply Chain / AI Models / AI Applications / Energy |
| `segment` | text | e.g. Semiconductors, Hyperscalers, Neoclouds, Data Centres, Power, Networking; Nuclear & Uranium, Clean Energy, Energy Storage, Power Generation, Oil & Gas |
| `subsegment` | text, nullable | e.g. Compute, Memory & Storage, Foundry |
| `role_notes` | text | |

Composite key: (`company_id`, `ai_category`).

### 2.3 `dim_model`
Grain: one row per named AI model (family or specific release). New — seeded from AI-model-provider companies in `dim_company`.

| Column | Type | Notes |
|---|---|---|
| `model_id` | text, PK | e.g. `gpt-5`, `claude-opus-5`, `deepseek-v4` |
| `company_id` | text, FK → `dim_company.company_id` | developing lab |
| `model_name` | text | display name |
| `model_family` | text | e.g. "GPT", "Claude", "Gemini" |
| `modality` | text | text / multimodal / code / image / etc. |
| `open_weight` | bool | |
| `first_release_date` | date | first public/API availability |

### 2.4 `dim_date`
Grain: one row per calendar date. Standard time dimension.

| Column | Type | Notes |
|---|---|---|
| `date` | date, PK | |
| `year`, `quarter`, `month`, `week`, `day_of_week` | int | |
| `is_trading_day` | bool | derived from a reference market calendar (equities); crypto trades 24/7 so this flag is equity-context only |

### 2.5 `dim_market`
Grain: one row per tradable instrument (equity ticker or crypto asset). Unifies equities and crypto under one dimension via an `asset_type` discriminator, so `fact_market_prices` has a single grain regardless of asset class.

| Column | Type | Notes |
|---|---|---|
| `market_id` | text, PK | e.g. `NVDA`, `BTC` |
| `asset_type` | text | `equity` \| `crypto` |
| `company_id` | text, FK → `dim_company.company_id`, nullable | populated for `equity` rows |
| `crypto_asset_id` | text, FK → `dim_crypto_asset.asset_id`, nullable | populated for `crypto` rows |
| `symbol` | text | ticker (equity) or trading symbol (crypto) |
| `currency` | text | quote currency, e.g. USD |
| `exchange` | text, nullable | null for crypto (venue-agnostic aggregate price) |

Exactly one of `company_id` / `crypto_asset_id` is non-null per row (enforced in ingestion validation, §5 of Stage 3 design).

### 2.6 `dim_crypto_asset`
Grain: one row per crypto asset. Source: `data/reference/crypto_assets.csv`, generated by `src.ingestion.crypto_universe`: the current top 10 by market cap (CoinCodex) plus the pinned BTC/ETH/SOL. Membership changes with the ranking.

| Column | Type | Notes |
|---|---|---|
| `asset_id` | text, PK | |
| `asset_name` | text | |
| `symbol` | text | |
| `category` | text | e.g. Layer 1, Payments, Meme, Oracle/Infrastructure |
| `launch_date` | date | |

### 2.7 `dim_sector`
Grain: one row per sector/category label used across `dim_company.industry` and `company_ai_categories.ai_category` and `dim_crypto_asset.category`. Kept as a thin lookup (label → display name / description) rather than a dimension every fact table joins against directly, since sector is already carried as an attribute on `dim_company`/`dim_crypto_asset`.

| Column | Type | Notes |
|---|---|---|
| `sector_id` | text, PK | slug of the category label |
| `sector_name` | text | |
| `sector_group` | text | `equity_industry` \| `ai_category` \| `crypto_category` |

### 2.8 `dim_news_source`
Grain: one row per news publisher.

| Column | Type | Notes |
|---|---|---|
| `source_id` | text, PK | |
| `source_name` | text | |
| `domain` | text | |
| `country` | text, nullable | |

## 3. Fact Tables

### 3.1 `fact_market_prices`
Grain: one row per (`market_id`, `date`). Replaces/generalizes the existing single-asset `sui_2023-05-09_2025-02-08.csv`.

| Column | Type | Notes |
|---|---|---|
| `market_id` | text, FK → `dim_market.market_id` | |
| `date` | date, FK → `dim_date.date` | |
| `open`, `high`, `low`, `close` | float | |
| `volume` | float | |
| `market_cap` | float, nullable | crypto only |
| `adj_close` | float, nullable | equities only (dividend/split adjusted) |

PK: (`market_id`, `date`). Data-quality constraints (Stage 3): `close > 0`, `volume >= 0`, `high >= low`, `high >= open`, `high >= close`, `low <= open`, `low <= close`.

### 3.2 `fact_news`
Grain: one row per captured article/headline.

| Column | Type | Notes |
|---|---|---|
| `news_id` | text, PK | hash of (source_id, url, timestamp) to dedupe |
| `timestamp` | datetime | |
| `source_id` | text, FK → `dim_news_source.source_id` | |
| `title` | text | |
| `description` | text, nullable | |
| `url` | text | |
| `matched_company_id` | text, FK → `dim_company.company_id`, nullable | result of entity matching (Stage 4) |
| `matched_asset_id` | text, FK → `dim_crypto_asset.asset_id`, nullable | |
| `category` | text | e.g. earnings, model-release, regulation, macro |

An article may match zero, one, or (rarely) both a company and a crypto asset; unmatched articles are still stored (`matched_*` null) rather than dropped, so entity-matching recall can be audited later.

### 3.3 `fact_sentiment`
Grain: one row per (`news_id`, `sentiment_model`) — supports storing VADER and TextBlob (and future FinBERT) scores for the same article side by side, per Stage 4's requirement to compare models rather than assume one is superior.

| Column | Type | Notes |
|---|---|---|
| `news_id` | text, FK → `fact_news.news_id` | |
| `sentiment_model` | text | `vader` \| `textblob` \| `finbert` \| ... |
| `sentiment_score` | float | model-native scale, documented per model |
| `sentiment_label` | text | derived category, thresholds documented in `src/sentiment/` |
| `scored_at` | datetime | pipeline run timestamp, for reproducibility |

PK: (`news_id`, `sentiment_model`).

### 3.4 `fact_model_release`
Grain: one row per model release/announcement event.

| Column | Type | Notes |
|---|---|---|
| `release_id` | text, PK | |
| `model_id` | text, FK → `dim_model.model_id` | |
| `release_date` | date | |
| `announcement_type` | text | major release / minor update / preview / deprecation |
| `source_url` | text, nullable | |

### 3.5 `fact_model_benchmark`
Grain: one row per (`model_id`, `benchmark_name`, `eval_date`).

| Column | Type | Notes |
|---|---|---|
| `model_id` | text, FK → `dim_model.model_id` | |
| `benchmark_name` | text | e.g. MMLU, GPQA, SWE-bench |
| `score` | float | |
| `eval_date` | date | |
| `source` | text | who ran/reported the eval |

### 3.6 `fact_company_event`
Grain: one row per material company event (earnings, product launch, partnership, regulatory action).

| Column | Type | Notes |
|---|---|---|
| `event_id` | text, PK | |
| `company_id` | text, FK → `dim_company.company_id` | |
| `event_date` | date | |
| `event_type` | text | earnings / product-launch / partnership / regulatory / other |
| `description` | text | |
| `source_url` | text, nullable | |

## 4. Multi-Everything Support (design check against Stage 2 requirements)

| Requirement | How the model supports it |
|---|---|
| Multiple companies | `dim_company` + bridge table, no hard cap |
| Multiple models | `dim_model` keyed by `model_id`, FK to any company |
| Multiple stocks | `dim_market` rows with `asset_type='equity'` |
| Multiple crypto assets | `dim_market` rows with `asset_type='crypto'` + `dim_crypto_asset` |
| Multiple news sources | `dim_news_source`, `fact_news.source_id` |
| Multiple sentiment systems | `fact_sentiment` grain includes `sentiment_model` |
| Multiple prediction horizons | not a stored fact — handled at the feature-engineering/target layer (Stage 6/7) by parameterizing horizon (1d/5d/10d) over `fact_market_prices`, so no schema change needed per horizon |

## 5. Explicit Non-Duplication Notes

- Company attributes (name, ticker, exchange, country) live **only** in `dim_company` — never repeated in `dim_market`, `fact_company_event`, etc., which all reference `company_id`.
- Sector/category labels are attributes on `dim_company` / `company_ai_categories` / `dim_crypto_asset`, not separately duplicated per fact row; `dim_sector` is a lookup for display/grouping only.
- Sentiment scores from multiple models are rows, not wide columns (`fact_sentiment` is long/tall), avoiding a schema change every time a new sentiment model is added.

## 6. What This Replaces From the Existing Repo

- `sui_2023-05-09_2025-02-08.csv` — **superseded and removed**: SUI has been excluded from the tracked crypto universe per current project decision (see `data/reference/crypto_assets.csv`); the legacy CSV has been deleted from the repository and is not a Stage 3 ingestion target unless SUI is reinstated later.
- `sui_crypto_headlines_sentiment_analysis.csv` → target shape is `fact_news` + `fact_sentiment`, once Stage 4 rebuilds entity-filtered scraping (the existing file's rows are not entity-clean enough to load as-is, per `PROJECT_AUDIT.md` §3c).

## 7. Stage 2 Completion Check

- [x] Minimum required dims/facts from the target prompt all defined (`dim_company, dim_model, dim_date, dim_market, dim_sector, dim_news_source, fact_market_prices, fact_news, fact_sentiment, fact_model_release, fact_model_benchmark, fact_company_event`)
- [x] Primary keys and relationships defined for every table
- [x] Duplication avoided (bridge table for multi-category, long-format sentiment table)
- [x] Explicitly supports multiple companies/models/stocks/crypto assets/news sources/sentiment systems/horizons (§4)
- [x] Reconciled against current `data/reference/*.csv` state, including the SUI-exclusion decision

**Stage 2 status: COMPLETE.**
