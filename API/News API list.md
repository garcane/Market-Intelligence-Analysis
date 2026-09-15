# News APIs and Financial News Sources — 2026 Reference

A consolidated reference of free and low-cost news APIs and financial-news sources for the **Market Intelligence Analysis** project.

> **Note:** Free-tier terms, quotas, rate limits, endpoint availability, and licensing can change frequently. Verify current provider documentation before implementation.

---

## Quick Comparison

| Provider | Primary Use | Access | Best For |
|---|---|---|---|
| **Marketaux** | Financial / stock news | API key | **Core financial news** |
| **GDELT** | Global and macro news | Open | Historical research and large-scale analysis |
| **Google News RSS** | General news | No key | Broad monitoring and RSS ingestion |
| **Bing News Search** | General / business news | API | Microsoft ecosystem |
| **Yahoo Finance / yfinance** | Company-specific financial news | Unofficial Python interface | Stock-linked news and broad market context |
| NewsAPI.org | General news | API key | Prototyping |
| GNews.io | General / multilingual news | API key | Simple projects |
| NewsData.io | International news | API key | Multilingual monitoring |
| The Guardian Open Platform | Single-publisher news | API key | Journalism/archive research |
| Newscatcher | General news | API key | Research |
| Currents API | Real-time news | API key | Live monitoring |

---

# Part 1 — Core Financial News

## 1. Marketaux

### Overview

Marketaux is a finance-focused news API designed around financial markets, companies, securities, entities, and market-related news.

### Best for

- Stock-specific news
- Financial dashboards
- Market monitoring
- Entity and ticker extraction
- News sentiment analysis
- Linking news to securities

### Strengths

- Finance-focused coverage
- Structured ticker/entity metadata
- Useful timestamps and publisher information
- Well suited to financial analytics pipelines

### Project role

**Core financial-news source.** Marketaux should be the primary structured source for stock and financial news.

---

## 2. Yahoo Finance / yfinance

### Overview

Yahoo Finance has a strong financial-news ecosystem, including company-specific news on stock pages and broader market coverage. However, there is an important distinction between Yahoo Finance as a website/data source and an official Yahoo Finance developer API.

Yahoo's current official developer API catalogue does **not** provide a general first-party Yahoo Finance News API. The historical Yahoo Finance API was discontinued, while current Python access through `yfinance` is an unofficial interface.

### Python example

```python
import yfinance as yf

ticker = yf.Ticker("AAPL")
news = ticker.news

for article in news:
    print(article)
```

### Best for

- Company-specific financial news
- Stock-linked news discovery
- Market context
- Combining price history and news in one Python workflow

### Strengths

- Convenient alongside Yahoo historical stock data
- Broad market coverage
- No separate news API key for common `yfinance` usage
- Useful for exploratory analysis and portfolio projects

### Limitations

- `yfinance` is unofficial
- Yahoo can change or restrict underlying endpoints
- News results can occasionally be poorly matched to the requested ticker
- Reliability and terms should be considered before using it as a production-critical dependency

### Project role

**Supplementary stock-news source** and useful companion to Yahoo Finance stock data. It should complement rather than replace Marketaux as the project's structured financial-news source.

---

# Part 2 — General and Macro News

## 3. GDELT Project APIs

- **Best for:** Academic research, large-scale analysis, macro news, AI training and historical research
- **Access:** Open / research-oriented
- **Coverage:** Global, multilingual
- **Strength:** Large-scale news monitoring and historical context
- **Limitation:** More complex than a conventional headline API

GDELT can identify people, locations, organisations, themes, emotions and other signals across global news.

### Project role

**Core supplementary source for macroeconomic, geopolitical and historical news analysis.**

---

## 4. Google News RSS

- **Best for:** Broad news monitoring and RSS ingestion
- **Access:** No API key
- **Format:** RSS/XML

Example topic feed:

```text
https://news.google.com/rss/search?q=your+topic&hl=en-US&gl=US&ceid=US:en
```

Top headlines:

```text
https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en
```

### Project role

**General-news supplementary source** with very low integration overhead.

---

## 5. Bing News Search

- **Best for:** General and business news
- **Historical free-tier reference:** 1,000 requests/month and 3 requests/second
- **Project role:** Supplementary general-news source

> **Important:** Microsoft has retired or changed several Bing Search APIs over time. Verify current availability and migration requirements before implementation.

---

# Part 3 — General News Aggregators

## 6. NewsAPI.org

- **Best for:** Prototyping, internal tools and academic projects
- **Free-tier reference:** 1,000 requests/day
- **Limitations:** Development-use restrictions, limited historical depth and attribution requirements may apply

Endpoints include `everything`, `top-headlines`, and `sources`.

```bash
curl "https://newsapi.org/v2/everything?q=tesla&sortBy=publishedAt&apiKey=API_KEY"
```

### Project role

**Experimental general-news source.**

---

## 7. GNews.io

- **Best for:** General and multilingual news
- **Free-tier reference:** 100 requests/day
- **Limitations:** Free-tier commercial restrictions may apply

### Project role

**Experimental general-news source.**

---

## 8. NewsData.io

- **Best for:** International and multilingual news monitoring
- **Free-tier reference:** 500 requests/day, subject to current plan
- **Strength:** Broad international coverage
- **Limitation:** Endpoint and historical-data availability varies by plan

Example:

```bash
curl "https://newsdata.io/api/1/news?apikey=YOUR_KEY&q=keyword&country=us"
```

### Project role

**Supplementary / experimental general-news source.**

---

## 9. Currents API

- **Best for:** Real-time monitoring, news tickers and dashboards
- **Free access:** Limited trial/free tier depending on current plan
- **Strength:** Immediacy
- **Limitation:** Smaller coverage and tighter limits than major aggregators

### Project role

**Experimental real-time news source.**

---

## 10. TheNewsAPI

- **Best for:** Small projects and low-volume news monitoring
- **Free-tier reference:** 100 requests/day
- **Limitation:** Low request limits and potentially limited historical depth

### Project role

**Experimental source.**

---

## 11. Mediastack

- **Best for:** Budget applications and API evaluation
- **Free-tier reference:** 100 requests/month
- **Limitations:** Data delay, historical restrictions and commercial-use limitations may apply

### Project role

**Experimental source.**

---

## 12. Newscatcher

- **Best for:** News research
- **Free-tier reference:** 1,000 requests/month
- **Rate limit reference:** 1 request/second

### Project role

**Research-oriented alternative.**

---

## 13. WorldNewsAPI

- **Best for:** Rapid project validation and international news
- **Free-tier reference:** 100 requests/day
- **Coverage:** International and multilingual

### Project role

**Experimental alternative.**

---

## 14. The Guardian Open Platform

- **Best for:** Journalism research, content analysis and archive research
- **Free-tier reference:** 5,000 calls/day
- **Limitation:** Single publisher and licensing/attribution requirements apply

### Project role

**Specialised research source.**

---

# Part 4 — Additional / Specialised Sources

## 15. Hacker News API

Useful for technology, startup and developer-related news.

- **Access:** Open
- **Best for:** Technology and startup monitoring

Base URL:

```text
https://hacker-news.firebaseio.com/v0
```

---

## 16. Spaceflight News API

Useful for space-industry and aerospace monitoring.

- **Access:** Open
- **Best for:** Spaceflight news

Base URL:

```text
https://api.spaceflightnewsapi.net/v3
```

---

## 17. SpaceX API

Useful for launch and aerospace data rather than conventional news.

- **Access:** Open
- **Best for:** Launch and mission data

Base URL:

```text
https://api.spacexdata.com/v5
```

---

## 18. Community NewsAPI

Community-maintained and self-hosted news aggregation projects can provide an alternative where full deployment control is desirable.

### Project role

**Experimental / self-hosted alternative.**

---

# Part 5 — Financial News Architecture

For the Market Intelligence Analysis project, financial news should be separated from general news because financial sources provide additional market-specific metadata.

```text
                         NEWS
                          │
             ┌────────────┴────────────┐
             │                         │
      FINANCIAL NEWS              GENERAL NEWS
             │                         │
      ┌──────┴──────┐          ┌──────┼──────┐
      │             │          │      │      │
  Marketaux     Yahoo/yfinance GDELT Google  Bing
      │             │          RSS
      └──────┬──────┘          │
             │                 │
             └────────┬────────┘
                      ▼
             News Standardisation
                      │
             Deduplication / QA
                      │
             Entity / Ticker Mapping
                      │
             Sentiment / Classification
                      │
                      ▼
              Market Intelligence
```

---

# Part 6 — Choosing the Right News Source

| Use Case | Recommended Source |
|---|---|
| Stock-specific financial news | **Marketaux** |
| Yahoo Finance-specific news | **Yahoo Finance / yfinance** |
| Broad global news | **GDELT** |
| No-key general news | **Google News RSS** |
| General / business news | **Bing News** |
| Simple general-news API | GNews / NewsAPI.org |
| International monitoring | NewsData.io / WorldNewsAPI |
| Historical research | **GDELT** |
| Technology / startup news | Hacker News API |
| Specialised aerospace news | Spaceflight News API |

---

# Part 7 — Recommended Stack for This Project

### Core

1. **Marketaux** — structured financial and stock news
2. **GDELT** — global, macro and historical news
3. **Google News RSS** — broad no-key news discovery
4. **Yahoo Finance / yfinance** — stock-linked news and Yahoo Finance context

### Supplementary

5. **Bing News** — general and business news
6. **NewsData.io / GNews** — additional general-news coverage

### Experimental

7. **NewsAPI.org**
8. **Currents API**
9. **Newscatcher**
10. **The Guardian Open Platform**
11. Other specialised sources as required

---

# Part 8 — Data Quality and Legal Considerations

Before using a source in a production pipeline, check:

1. **Commercial-use rights** — free access does not necessarily mean unrestricted commercial use.
2. **Attribution requirements** — some providers require visible attribution.
3. **Rate limits** — ensure the quota is sufficient for the intended ingestion schedule.
4. **Historical depth** — confirm that the provider exposes the period required for analysis.
5. **Data freshness** — a daily free-tier pull may not capture fast-moving events.
6. **Deduplication** — the same article may appear through multiple aggregators.
7. **Entity mapping** — map companies and tickers consistently across providers.
8. **Copyright** — API access does not automatically grant rights to republish full article content.
9. **Unofficial interfaces** — treat wrappers such as `yfinance` differently from official APIs when assessing reliability and terms.

---

# Final Recommendation

The preferred architecture is to use **Marketaux as the primary financial-news API**, supported by **Yahoo Finance / yfinance**, **GDELT**, **Google News RSS**, and **Bing News** for broader coverage and validation.

This gives the project several independent perspectives:

```text
Marketaux
    └── Financial / stock-specific news

Yahoo Finance / yfinance
    └── Stock-linked news and market context

GDELT
    └── Global / macro / historical context

Google News RSS
    └── Broad general-news discovery

Bing News
    └── General / business-news coverage
            │
            ▼
      Unified News Dataset
            │
      ├── Deduplication
      ├── Entity mapping
      ├── Ticker mapping
      ├── Sentiment
      ├── Topic classification
      └── Market-event analysis
```

*Compiled September 2026. Verify all current quotas, licensing conditions and terms before implementation.*
