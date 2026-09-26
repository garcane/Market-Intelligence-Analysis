# AI Market Intelligence & Financial Analytics Platform

## Project Context
This project represents a major refactoring and expansion of the original SUI Crypto Sentiment Analysis project. As mapped out in the **Fintech Analysis Mapping.pdf**, the objective has evolved from predicting a single cryptocurrency asset to building a robust, quantitative financial intelligence system. This platform analyzes the entire Artificial Intelligence value chain, correlating NLP-derived media sentiment, model benchmarks, and supply chain dependencies with global equity and crypto market reactions.

---

## Platform Architecture

The platform is designed to model the downstream financial impact of the AI industry. It splits the ecosystem into two primary tracks: **Model Providers** and **AI Infrastructure**.

### 1. The AI Industry Taxonomy
**Frontier AI Model Companies**
*   **US/Western:** OpenAI, Anthropic, Google DeepMind / Alphabet, xAI, Meta, Microsoft, Mistral
*   **Chinese:** DeepSeek, Alibaba / Qwen, Moonshot AI / Kimi, Zhipu AI / GLM, Baidu / ERNIE, MiniMax, Tencent

**AI Infrastructure & Semiconductor Equities**
*   **Compute:** NVIDIA, AMD, Broadcom, Intel
*   **Foundry/Manufacturing:** TSMC, ASML, Applied Materials, Lam Research
*   **Memory/Storage:** Micron, SK Hynix, Samsung, SanDisk, Seagate
*   **Networking:** Broadcom, Arista Networks, Cisco, Marvell
*   **Cloud Infrastructure:** Microsoft, Alphabet, Amazon, Oracle, Meta, CoreWeave

### 2. Conceptual Pipeline
`Financial News` → `Web Scraping` → `NLP Sentiment Analysis` → `Market Data Aggregation` → `Statistical Analysis` → `ML Classification Pipeline` → `Interactive Dashboard`

---

## Data Engineering & Schemas

The data architecture relies on several interconnected relational tables to create derived metrics:

*   **`companies`**: `ticker`, `country`, `sector`, `category`, `market_cap`
*   **`models`**: `model_name`, `company`, `release_date`, `model_type`, `context_window`, `open_weights`
*   **`model_benchmarks`**: `model`, `benchmark`, `score`, `date`
*   **`news`**: `timestamp`, `company`, `headline`, `source`, `url`, `sentiment`, `sentiment_score`
*   **`market_data`**: `timestamp`, `ticker`, `open`, `high`, `low`, `close`, `volume`
*   **`ai_relationships`**: `company`, `supplier`, `relationship_type`, `dependency`

---

## Quantitative Research & Synthetic Indices

### Core Analytical Questions
Instead of simply predicting asset direction, this platform addresses targeted financial questions:
*   Does positive AI news sentiment translate into abnormal stock returns?
*   Do semiconductor stocks move together during major AI model announcements?
*   Which segment of the AI supply chain exhibits the highest volatility?
*   Does Chinese AI news produce different market reactions compared to US AI news?
*   Does AI infrastructure sentiment lead semiconductor returns?

### AI Investment Theme Indices
The platform constructs and tracks custom synthetic indices to compare against standard benchmarks (S&P 500, Nasdaq-100, SOX, BTC, ETH):
*   **AI Infrastructure Index:** (e.g., NVDA 20%, TSMC 15%, AVGO 15%, ASML 10%, AMD 10%, MU 10%, etc.)
*   **AI Platform Index**
*   **AI Consumer Index**

*Statistical outputs include:* Returns, Volatility, Sharpe Ratio, Maximum Drawdown, Beta, Rolling Correlation, and Event Reactions.

---

## Machine Learning Comparison: Market Movement Classification

The predictive component of this project moves beyond simple binary up/down forecasting. It focuses on identifying significant short-term market opportunities. 

**Target Definition:** 
Predict whether an asset will generate a positive return exceeding a defined threshold over the next $N$ trading days (e.g., `Target = 1 if future_5d_return > 2% else 0`).

### Model Leaderboard
We evaluate four distinct algorithms on the exact same dataset, features, and train/test splits to determine the best approach for tabular financial data:

1.  **Logistic Regression:** Acts as our interpretable, linear baseline.
2.  **Random Forest Classifier:** Captures non-linear relationships using bagging/independent tree construction.
3.  **XGBoost:** Primary high-performance gradient-boosting model.
4.  **HistGradientBoosting:** Secondary boosting benchmark, natively optimized by scikit-learn for speed on large tabular datasets.

### Evaluation Metrics
Models are evaluated across a rigorous financial framework, not just raw accuracy:
*   **Performance:** ROC-AUC, PR-AUC, F1-Score, Precision, Recall, Accuracy, Confusion Matrix.
*   **Operational:** Training time, Prediction time.
*   **Interpretability:** Calibration (probability quality), Feature Importance.

---

*This project bridges the gap between alternative data engineering (NLP, Web Scraping) and institutional-grade financial risk/quantitative modeling.*