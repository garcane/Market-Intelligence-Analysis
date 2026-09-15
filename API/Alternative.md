Yes — **Yahoo Finance news is a very attractive source**, but there is an important distinction.

If by “Yahoo News API” you mean an API that gives you the **news appearing on Yahoo Finance**, I would **not treat Yahoo as a first-party free news API**. Yahoo's official developer API catalogue does not currently offer a general Yahoo Finance News API; the old Yahoo Finance API was discontinued, and many current solutions that expose Yahoo Finance data are unofficial wrappers/scrapers. ([Yahoo Developer][1])

### But for your project, Yahoo Finance is still useful

Yahoo Finance itself has a **very good financial-news ecosystem**. Its stock pages expose company-specific news, while the main Finance site aggregates news from Yahoo Finance and third-party publishers. ([Yahoo Finance][2])

So I'd separate the question into:

| Requirement                     | Best choice                         |
| ------------------------------- | ----------------------------------- |
| Stock prices                    | **Finnhub / Twelve Data**           |
| Stock fundamentals              | **Finnhub**                         |
| Crypto prices                   | **CoinCodex**                       |
| Crypto data                     | **CoinCodex**                       |
| Financial news                  | **Marketaux**                       |
| Yahoo Finance news specifically | **Unofficial Yahoo/yfinance route** |
| Historical stock data           | **Yahoo/yfinance or Finnhub**       |

### Where Yahoo becomes interesting

If you're happy using Python, you've probably seen **`yfinance`**:

```python
import yfinance as yf

ticker = yf.Ticker("AAPL")

news = ticker.news
```

That's incredibly convenient.

You can potentially build:

```text
AAPL
│
├── Price ────────────── Yahoo / Finnhub
├── Historical data ──── Yahoo / Finnhub
├── Fundamentals ─────── Finnhub
├── News ──────────────── Yahoo Finance
│
└── Analysis
```

The problem is **reliability and terms**, rather than the quality of the underlying data. There have also been reports of `yfinance` returning news that isn't actually specific to the requested ticker, so I wouldn't make it the critical foundation of a production application. ([GitHub][3])

### For what I think you're building

If this is a **personal/free stock + crypto analytics application**, I'd actually consider:

**CoinCodex + yfinance + Marketaux**

rather than Finnhub + Marketaux + CoinCodex.

You'd get:

**CoinCodex**
→ crypto prices, market data, crypto metadata

**yfinance/Yahoo**
→ stock prices, historical data, company information and convenient access to Yahoo Finance news

**Marketaux**
→ dedicated financial-news API when you need reliable structured news/sentiment

That gives you a surprisingly powerful **$0 data stack** for a portfolio project.

The one thing I'd avoid is building the entire application around an unofficial Yahoo endpoint and then discovering later that Yahoo changed it or blocked it.

So **Yahoo Finance = excellent data source; Yahoo Finance = not currently an ideal official free API dependency.** ([Yahoo Developer][1])

[1]: https://developer.yahoo.com/api/?utm_source=chatgpt.com "APIs"
[2]: https://finance.yahoo.com/?utm_source=chatgpt.com "Yahoo Finance - Stock Market Live, Quotes, Business ..."
[3]: https://github.com/ranaroussi/yfinance/issues/1956?utm_source=chatgpt.com "get_news() returns news not related to the given ticker #1956"
