# Cryptocurrency Data Sources

A research reference for cryptocurrency market-data sources suitable for the **Market Intelligence Analysis** project.

> **Note:** This document records the research and alternatives considered during source selection. Free-tier quotas, API availability, licensing, and terms can change, so provider documentation should be checked before implementation.

---

## 1. Recommended Cryptocurrency Data Source

| Provider | Primary Use | API Key | Project Role |
|---|---|---:|---|
| **CoinCodex** | Crypto prices, market data, metadata, historical data | Yes / API access | **Selected core source** |
| CoinGecko | Prices, market data, metadata | Yes for API access | Alternative |
| CoinMarketCap | Prices, market data, rankings, metadata | Yes | Alternative |
| CryptoCompare | Prices, historical data, market data | Yes | Alternative |
| Binance API | Exchange-level market data | No for many public endpoints | Exchange-specific alternative |
| CoinPaprika | Prices, market data, historical data | No for basic access | Alternative |
| Alpha Vantage | Crypto and broader financial data | Yes | Cross-asset alternative |

---

## 2. CoinCodex — Selected Source

### Overview

CoinCodex provides cryptocurrency market data covering assets, prices, market capitalisation, volume, historical charts, exchanges, trading pairs, metadata, and additional asset information.

The CoinCodex API is particularly suitable for this project because it can provide cryptocurrency data alongside the broader stock and news datasets being developed in the repository.

### Useful data categories

- Cryptocurrency prices
- Market capitalisation
- Trading volume
- Historical price data
- Asset metadata
- Exchanges and trading pairs
- Categories
- Social information
- Cryptocurrency news where supported by the API

### Project role

**Core cryptocurrency data source.**

CoinCodex is the selected provider for the project's main cryptocurrency dataset.

### Important consideration

CoinCodex's current API documentation describes the API as beta and subject to change. Its API licence also places restrictions on commercial use and requires attribution. These conditions should be reviewed before using the project commercially.

---

## 3. CoinGecko

### Overview

CoinGecko is one of the most widely used cryptocurrency data providers and offers extensive coverage of coins, tokens, exchanges, market data, metadata, and historical information.

### Best for

- Broad asset coverage
- Market capitalisation
- Trading volume
- Historical prices
- Token metadata
- Exchange data
- Portfolio and market-analysis projects

### Strengths

- Large cryptocurrency universe
- Strong historical market-data coverage
- Widely used by developers and analysts
- Good ecosystem of documentation and integrations

### Limitations

- API access and rate limits depend on the current plan
- Some functionality is restricted compared with paid tiers

### Project role

**Strong alternative to CoinCodex** and a useful benchmark if additional coverage is required.

---

## 4. CoinMarketCap

### Overview

CoinMarketCap provides cryptocurrency prices, rankings, market capitalisation, trading volume, supply information, metadata, and exchange data.

### Best for

- Market rankings
- Market-cap analysis
- Asset discovery
- Exchange information
- Broad cryptocurrency coverage

### Strengths

- Very broad market coverage
- Strong recognition as a cryptocurrency market-data provider
- Useful rankings and metadata

### Limitations

- API access requires an API key
- Free access is rate-limited
- Some advanced data requires paid access

### Project role

**Alternative / validation source** for market-cap and asset-ranking data.

---

## 5. CryptoCompare

### Overview

CryptoCompare provides cryptocurrency market data, historical prices, exchange information, social data, and other digital-asset metrics.

### Best for

- Historical cryptocurrency prices
- Exchange-level data
- Market analysis
- Cross-exchange comparisons
- Digital-asset research

### Project role

**Alternative source** for historical and exchange-level validation.

---

## 6. Binance API

### Overview

Binance provides public market-data endpoints for assets traded on its exchange.

### Best for

- Exchange prices
- Trading pairs
- Order-book data
- Candlestick data
- High-frequency exchange-level analysis

### Limitation

Binance represents **one exchange**, rather than the entire cryptocurrency market. Its prices can therefore differ from aggregated market prices.

### Project role

**Exchange-specific / supplementary source** rather than the main cryptocurrency dataset.

---

## 7. CoinPaprika

### Overview

CoinPaprika provides cryptocurrency prices, market data, historical data, asset metadata, and exchange information.

### Best for

- Cryptocurrency discovery
- Historical market data
- Market-cap comparisons
- Asset metadata

### Project role

**Alternative free source** for cross-validation and additional asset coverage.

---

## 8. Alpha Vantage

Alpha Vantage covers multiple financial markets, including cryptocurrency data, alongside equities, foreign exchange, and technical indicators.

### Best for

- Cross-asset analysis
- Cryptocurrency prices
- Technical indicators
- Combining stock and crypto research through one provider

### Project role

**Experimental cross-asset source**, rather than the primary crypto provider.

---

## 9. Comparison

| Provider | Coverage | Historical Data | Exchange Data | Metadata | Recommended Role |
|---|---|---|---|---|---|
| **CoinCodex** | Broad | Yes | Yes | Yes | **Core / selected** |
| CoinGecko | Very broad | Yes | Yes | Yes | Alternative |
| CoinMarketCap | Very broad | Yes | Yes | Yes | Alternative / validation |
| CryptoCompare | Broad | Yes | Yes | Yes | Alternative |
| Binance | Exchange-specific | Yes | Yes | Limited | Exchange data |
| CoinPaprika | Broad | Yes | Yes | Yes | Alternative |
| Alpha Vantage | Broad financial API | Yes | Limited | Yes | Cross-asset alternative |

---

## 10. Selection Criteria

The sources were considered against the following criteria:

1. **Asset coverage** — number and diversity of cryptocurrencies available.
2. **Historical depth** — availability of historical price and market data.
3. **Market metadata** — market cap, volume, supply, categories, exchanges and related information.
4. **API accessibility** — documentation, authentication requirements and ease of integration.
5. **Free-tier suitability** — whether the provider is practical for a portfolio/research project without significant cost.
6. **Reliability** — consistency and stability of the data source.
7. **Cross-validation potential** — usefulness alongside other independent providers.
8. **Licensing** — commercial-use restrictions, attribution requirements and redistribution rules.

---

## 11. Final Recommendation

For this project, the preferred architecture is:

```text
CRYPTOCURRENCY DATA
        │
        ▼
    CoinCodex
        │
        ├── Prices
        ├── Market Cap
        ├── Volume
        ├── Historical Data
        ├── Metadata
        └── Market / Asset Information
                │
                ▼
        Standardised Crypto Dataset
                │
                ▼
       Market Intelligence Analysis
```

**CoinCodex is therefore the selected core cryptocurrency source.** The other providers remain useful as documented alternatives for future expansion, validation, or specialist exchange-level analysis.
