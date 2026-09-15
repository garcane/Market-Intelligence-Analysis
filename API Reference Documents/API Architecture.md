# Market Intelligence API Architecture

## Overview

The Market Intelligence Analysis project uses a multi-source API architecture rather than relying on a single provider. Sources are organised by their primary purpose and by how central they are to the project.

The architecture is designed to provide broad market coverage, redundancy, cross-validation and specialist data sources for equities, cryptocurrency and financial/general news.

> **Important:** API quotas, availability, licensing and terms of use change frequently. Verify provider documentation before implementation and before deploying the project commercially.

---

## Tier 1 — Core Data Sources

These are the primary sources for the project and should form the main data pipeline.

### 1. CoinCodex — Cryptocurrency

**Primary use:** Cryptocurrency market data

- Cryptocurrency prices
- Market capitalisation
- Trading volume
- Historical market data
- Coin metadata
- Categories and related market information
- Exchange and trading-pair information
- Crypto analysis and related data

**Role:** Primary cryptocurrency data source.

---

### 2. Yahoo Finance / yfinance — Stocks

**Primary use:** Broad equity-market coverage

- Current and historical stock prices
- OHLCV data
- Company information
- Market data
- Historical time series
- Broad international equity coverage

**Role:** Primary stock-market data source.

**Implementation note:** `yfinance` provides a convenient Python interface to Yahoo Finance data. It should be treated as an unofficial interface rather than a guaranteed first-party Yahoo Finance developer API. Review Yahoo's applicable terms before commercial deployment.

---

### 3. Finnhub — Stocks and Financial Market Data

**Primary use:** Structured financial-market and company data

- Stock quotes
- Company profiles
- Fundamentals
- Financial statements
- Earnings
- Dividends
- Analyst recommendations
- Insider transactions
- Market data
- Company-related financial information

**Role:** Secondary/core stock data source that complements Yahoo Finance and can be used for validation and additional financial fields.

---

### 4. Marketaux — Financial News

**Primary use:** Financial and stock-specific news

- Financial news
- Company/ticker mentions
- Financial entities
- Publisher information
- Timestamps
- Sentiment-related information
- Equity and market-related topics

**Role:** Primary structured financial-news source.

---

## Tier 2 — Supplementary Sources

These sources extend the core pipeline with broader coverage, additional perspectives and fallback data.

### 5. GDELT — Global and Macro News

**Primary use:** Global news monitoring and historical research

- Global news coverage
- Multilingual monitoring
- Historical news research
- Organisations, people and locations
- Themes and events
- Sentiment/emotion-related signals

**Role:** Broad macro/general news intelligence and research source.

---

### 6. Google News RSS — General News

**Primary use:** Broad news discovery without an API key

- Topic searches
- General headlines
- Business and financial topics
- RSS/XML feeds
- Simple integration

**Role:** Lightweight supplementary news source and useful fallback for broad coverage.

---

### 7. Bing News — General/Business News

**Primary use:** Additional general and business news coverage

- News search
- Business news
- Topic monitoring
- Additional source diversity

**Role:** Supplementary news source that provides an alternative search/news ecosystem.

> **Note:** Microsoft has changed and retired parts of its Bing Search API offering over time. Verify the current product, pricing and migration path before implementation.

---

### 8. StockPrices.dev — Alternative Stock Quotes

**Primary use:** Lightweight stock quote retrieval

- Stock quotes
- Price information
- Change information
- Simple API access

**Role:** Lightweight alternative/fallback for stock-price retrieval and API experimentation.

---

## Tier 3 — Experimental / Alternative Sources

These sources should be retained for comparison, experimentation, validation or future expansion rather than being mandatory dependencies for the core pipeline.

### 9. Alpha Vantage — Alternative Financial Data

**Primary use:** Alternative stock and financial-market data

- Stock prices
- Historical data
- Fundamentals
- Technical indicators
- Forex
- Cryptocurrency
- Financial news and sentiment

**Role:** Alternative source for cross-validation and additional financial datasets.

---

### 10. Financial Modeling Prep (FMP) — Alternative Financial Data

**Primary use:** Alternative market and fundamental data

- Stock quotes
- Company profiles
- Fundamentals
- Financial statements
- Market data
- Other financial datasets

**Role:** Experimental/alternative source for comparison with Yahoo Finance and Finnhub.

---

### 11. NewsAPI.org — General News

**Primary use:** General news aggregation and prototyping

- General news search
- Top headlines
- Source information
- Keyword-based article discovery

**Role:** Experimental/general-news source rather than a core financial-news dependency.

> **Note:** The free tier has development/non-commercial restrictions. Verify current terms before use.

---

## Architecture by Data Domain

| Data Domain | Primary | Supplementary | Experimental / Alternative |
|---|---|---|---|
| Cryptocurrency | CoinCodex | — | Alpha Vantage |
| Stock prices | Yahoo Finance / yfinance | StockPrices.dev | Alpha Vantage, FMP |
| Stock fundamentals | Finnhub | Yahoo Finance | Alpha Vantage, FMP |
| Financial news | Marketaux | Finnhub | NewsAPI.org |
| General news | Google News RSS | Bing News, GDELT | NewsAPI.org |
| Macro / global news | GDELT | Google News RSS, Bing News | — |

---

## Multi-Source Validation Strategy

Where multiple sources provide the same type of information, the project can compare and validate results rather than treating one provider as an unquestionable source of truth.

### Example — Stock prices

```text
Yahoo Finance
      │
      ├─────────────┐
      │             │
      ▼             ▼
  Finnhub      StockPrices.dev
      │             │
      └──────┬──────┘
             ▼
      Validation Layer
             │
             ▼
       Stock Dataset
```

### Example — Financial and general news

```text
              NEWS PIPELINE
                    │
      ┌─────────────┼──────────────┐
      │             │              │
  Marketaux       GDELT       Google News RSS
      │             │              │
 Financial       Global          General
  markets        /macro          coverage
      │             │              │
      └─────────────┼──────────────┘
                    ▼
             News Ingestion
                    │
             Deduplication
                    │
             Classification
                    │
             Entity Mapping
                    │
             Sentiment/NLP
                    │
                    ▼
          Market Intelligence
```

---

## Recommended Data Flow

```text
API SOURCES
    │
    ▼
Ingestion Layer
    │
    ├── API authentication
    ├── Rate-limit handling
    ├── Retries
    └── Source metadata
    │
    ▼
Standardisation Layer
    │
    ├── Common schemas
    ├── Timestamp normalisation
    ├── Ticker/entity mapping
    ├── Currency handling
    └── Data-type validation
    │
    ▼
Quality & Deduplication
    │
    ├── Duplicate detection
    ├── Missing-value checks
    ├── Source comparison
    └── Freshness checks
    │
    ▼
Storage Layer
    │
    ├── Market data
    ├── Company data
    ├── Crypto data
    └── News data
    │
    ▼
Analytics Layer
    │
    ├── Price analytics
    ├── Financial analysis
    ├── News sentiment
    ├── Entity trends
    └── Market intelligence
    │
    ▼
Dashboard / AI / Reporting
```

---

## Design Principle

The project should **not** depend unnecessarily on a single provider. Specialist sources are preferred for their strongest use cases, while overlapping providers can be retained for validation, resilience and future experimentation.

The intended hierarchy is therefore:

**Core → reliable primary data sources**  
**Supplementary → additional coverage and independent signals**  
**Experimental → alternatives, validation and future development**

This approach keeps the project modular and makes individual API providers replaceable without redesigning the entire data pipeline.
