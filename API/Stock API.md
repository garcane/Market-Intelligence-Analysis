# Stock Data APIs

A structured reference for free and low-cost APIs suitable for stock prices, historical market data, company information, fundamentals, and financial market data.

> **Note:** Free-tier quotas, rate limits, endpoint availability, and licensing terms can change. Verify the provider's current documentation before production use.

---

## 1. Recommended Stock Data Stack

| Provider | Primary Use | API Key | Best For |
|---|---|---:|---|
| **Yahoo Finance / yfinance** | Prices, historical data, company information | No | Broad stock coverage and Python analysis |
| **Finnhub** | Prices, fundamentals, company data, market news | Yes | Structured financial market data |
| **StockPrices.dev** | Stock quotes | No | Lightweight quote retrieval |
| **Alpha Vantage** | Prices, technical indicators, fundamentals | Yes | Supplementary market data |
| **Financial Modeling Prep (FMP)** | Quotes, fundamentals, financial statements | Yes | Alternative financial data |

### Recommended approach for this project

**Yahoo Finance / yfinance + Finnhub** should form the main stock-data layer, with StockPrices.dev, Alpha Vantage, and FMP retained as supplementary or experimental sources.

```text
                    STOCK DATA
                        │
          ┌─────────────┴─────────────┐
          │                           │
   Yahoo Finance / yfinance        Finnhub
          │                           │
   Prices + History             Fundamentals
   Company information          Market data
          │                     Financial news
          └─────────────┬─────────────┘
                        │
                 Standardised Data
                        │
              Validation / Analytics
```

---

## 2. Yahoo Finance / yfinance

### Overview

Yahoo Finance is a broad source of equity market information. `yfinance` is an unofficial Python interface that provides convenient programmatic access to Yahoo Finance data.

### Best for

- Current and historical stock prices
- Company information
- Historical market data
- Dividends and splits
- Convenient Python-based analysis
- Broad ticker coverage

### Python example

```python
import yfinance as yf

stock = yf.Ticker("AAPL")

history = stock.history(period="1y")
info = stock.info
news = stock.news

print(history.head())
```

### Strengths

- Very convenient for Python workflows
- Broad coverage
- No API key required for common `yfinance` usage
- Strong historical-data functionality
- Well suited to exploratory analysis and portfolio projects

### Limitations

- `yfinance` is not an official Yahoo Finance developer API
- Yahoo can change or restrict underlying endpoints
- Reliability and terms should be considered before production use
- News returned through unofficial interfaces may occasionally be poorly matched to a ticker

### Project role

**Core stock source**, particularly for broad coverage and historical price data, but should be paired with an official structured financial API where reliability is important.

---

## 3. Finnhub

### Overview

Finnhub provides structured financial-market data through an API, including stock prices, company fundamentals, economic data, alternative data, and financial news.

### Best for

- Real-time market data
- Company fundamentals
- Financial statements and metrics
- Company profiles
- Market news
- Supplementing and validating Yahoo Finance data

### Authentication

Requires an API key.

### Project role

**Core stock-data source** and the main structured counterpart to Yahoo Finance.

---

## 4. StockPrices.dev

### Overview

StockPrices.dev provides a lightweight stock quote endpoint without requiring an API key.

### Endpoint

```text
https://stockprices.dev/api/stocks/{TICKER}
```

Replace `{TICKER}` with a ticker such as `AAPL`.

### Example

```bash
curl "https://stockprices.dev/api/stocks/AAPL"
```

### Best for

- Simple stock-price lookups
- Prototyping
- Lightweight applications
- Independent quote validation

### Project role

**Supplementary / alternative quote source.**

---

## 5. Alpha Vantage

### Overview

Alpha Vantage provides APIs covering stock prices, technical indicators, foreign exchange, cryptocurrencies, and other financial data.

### Authentication

Requires a free API key.

### Free-tier consideration

The standard free service has historically imposed relatively low request limits. Verified open-source and educational projects may have access to higher limits, subject to Alpha Vantage's current terms.

### Best for

- Technical indicators
- Stock quotes
- Historical data
- Supplementary financial analysis

### Project role

**Experimental / alternative source** for cross-checking and specialist indicators.

---

## 6. Financial Modeling Prep (FMP)

### Overview

Financial Modeling Prep provides market data, company profiles, financial statements, ratios, estimates, and other financial datasets.

### Authentication

Requires an API key.

### Best for

- Financial statements
- Company fundamentals
- Ratios and valuation data
- Historical market data
- Alternative financial datasets

### Project role

**Experimental / alternative financial-data source.**

---

## 7. Source Selection by Requirement

| Requirement | Primary Source | Secondary Source |
|---|---|---|
| Current stock price | Yahoo Finance / yfinance | Finnhub |
| Historical prices | Yahoo Finance / yfinance | Finnhub |
| Company information | Yahoo Finance / yfinance | Finnhub |
| Fundamentals | Finnhub | FMP |
| Financial statements | Finnhub | FMP |
| Technical indicators | Alpha Vantage | Yahoo Finance |
| Lightweight quote lookup | StockPrices.dev | Yahoo Finance |
| Cross-source validation | Yahoo Finance | Finnhub / StockPrices.dev |

---

## 8. Data Quality and Validation Strategy

Where practical, the project should avoid depending on a single stock-data provider.

```text
Ticker
  │
  ├── Yahoo Finance / yfinance
  │
  ├── Finnhub
  │
  └── StockPrices.dev
        │
        ▼
   Compare / Validate
        │
        ▼
 Standardised Stock Dataset
```

Useful validation checks include:

- Ticker consistency
- Price differences between providers
- Timestamp and market-session differences
- Missing observations
- Currency mismatches
- Duplicate records
- Corporate actions such as splits and dividends

---

## 9. Final Recommendation

For the **Market Intelligence Analysis** project:

1. **Yahoo Finance / yfinance** — primary broad stock-data source
2. **Finnhub** — structured financial-data and fundamentals source
3. **StockPrices.dev** — lightweight independent quote source
4. **Alpha Vantage** — technical indicators and supplementary data
5. **Financial Modeling Prep** — alternative fundamentals and financial statements

This provides broad coverage while keeping multiple independent sources available for validation and future expansion.
