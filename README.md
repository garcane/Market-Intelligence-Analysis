# SUI Cryptocurrency Sentiment Analysis and Price Prediction

## Project Overview
This project provides an in-depth analysis of cryptocurrency news sentiment related to the SUI token and predicts future price movements using machine learning models. The project integrates web scraping, natural language processing (NLP), and machine learning techniques to analyze how market sentiment impacts price trends.

## What is SUI?

SUI is the native coin of the Sui network, a layer-1 blockchain platform designed for global adoption that utilizes a novel object-centric data model and the Move programming language. The SUI coin has a capped total supply of 10 billion.

Key aspects of the SUI coin and the Sui network include:
*   **Functionality** SUI serves as the network's currency and is used for paying transaction fees (gas fees) and storage. It can be staked to participate in the network's proof-of-stake mechanism. SUI is also a versatile and liquid asset for various applications within the Sui ecosystem.
*   **Proof-of-Stake (PoS) Mechanism:** The Sui network uses a delegated proof-of-stake (PoS) consensus mechanism where validators lock up SUI as collateral and earn rewards for processing operations. Users can delegate their SUI to validators and earn rewards.
*   **Tokenomics:** Sui's tokenomics are designed to support the long-term financial needs of Web3. The tokenomics structure includes a vesting schedule to enhance network stability. There were no SUI airdrops to support the launch of the Mainnet network.
*   **Storage Fund:** Sui utilizes a storage fund, which is a cache of SUI that collects fees from on-chain transactions that add data to the chain. The storage fund is used to compensate validators for storage costs, and it also contributes to the deflationary aspect of the network.
*   **Deflationary Aspects** The capped total supply of SUI and the storage fund contribute to the deflationary nature of the network. Increased activity on the network leads to a larger storage fund, which reduces the amount of SUI in circulation.
*   **Validator Rewards** Sui uses a novel approach to reward validators, where all honest validators receive staking rewards based only on the amount of stake they hold, removing randomness from the equation. Each validator on Sui maintains its own staking pool that tracks the amount of stake and compounds rewards over time.
*   **Technology**: Sui’s architecture features low-latency transactions with stable fees, high throughput through horizontal scaling and parallelized execution. The object-oriented design of Sui allows developers to create objects tailored to their needs with inherent network-wide compatibility. Sui uses the Move programming language for its smart contracts, which is designed to be safe and expressive.
*  **Transactions**: Transactions on Sui are executed in parallel, and many transactions can be finalized and settled in less than half a second.
*   **zkLogin**: Sui uses zkLogin to enable users to create and manage accounts using web logins.

The Sui network is maintained by a permissionless set of authorities, similar to validators on other blockchains. It uses a Byzantine consistent broadcast protocol between authorities to ensure safety of operations on assets, while relying on Byzantine agreement for shared objects, governance and check-pointing.

Sui's native token, SUI, is used for staking, paying gas fees, and as a versatile asset within its ecosystem. The network uses a storage fund, a mechanism that adds a deflationary aspect to SUI. Validators play a key role in securing the network by processing transactions and are rewarded in proportion to their stake. The Sui network also supports light clients and bridges to other blockchains.


## Features
- **Sentiment Analysis**: Utilizes TextBlob and VADER sentiment analysis tools to classify news headlines as Bullish, Slightly Bullish, Neutral, Slightly Bearish, or Bearish.
- **Web Scraping**: Extracts news articles from multiple financial sources, including Crypto News and Yahoo Finance, to gather sentiment-related insights.
- **Data Cleaning & Preprocessing**: Uses NLP techniques such as tokenization, lemmatization, stopword removal, and regex cleaning to refine the text data.
- **Visualization & Insights**:
  - Time-series sentiment trend analysis
  - Histogram distributions of sentiment scores
  - Scatter plots comparing TextBlob and VADER sentiment scores
- **Machine Learning Model (XGBoost)**:
  - Processes historical price data combined with sentiment scores
  - Predicts future SUI cryptocurrency prices
  - Evaluates model performance using R-squared and Mean Absolute Error (MAE)

## Technologies Used
- **Programming Language**: Python
- **Data Handling & Analysis**:
  - `pandas`, `numpy`
- **Web Scraping**:
  - `BeautifulSoup`, `requests`
- **Natural Language Processing**:
  - `TextBlob`, `VADER SentimentIntensityAnalyzer`, `NLTK`
- **Visualization**:
  - `matplotlib`, `seaborn`
- **Machine Learning**:
  - `XGBoost`, `scikit-learn`

## Installation
### Prerequisites
Ensure you have Python 3.8 or later installed.

1. Clone the repository:
   ```sh
   git clone https://github.com/your-repo-name.git
   cd your-repo-name
   ```
2. Create a virtual environment and activate it:
   ```sh
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   venv\Scripts\activate     # On Windows
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Download necessary NLTK resources:
   ```python
   import nltk
   nltk.download('punkt')
   nltk.download('stopwords')
   nltk.download('wordnet')
   ```

## Usage
### Running Sentiment Analysis
Run the following command to scrape news headlines and perform sentiment analysis:
```sh
python main.py
```
This script will:
- Collect crypto news headlines from multiple sources
- Apply NLP preprocessing
- Perform sentiment analysis using TextBlob and VADER
- Save the processed data in `sui_crypto_headlines_sentiment_analysis.csv`
- Generate visualizations of sentiment trends over time

### Running the XGBoost Model
Execute the Jupyter Notebook to run the machine learning model:
```sh
jupyter notebook main_xgboost.ipynb
```
This notebook will:
- Load the historical SUI cryptocurrency price dataset (`sui_2023-05-09_2025-02-08.csv`)
- Preprocess and engineer features including sentiment scores
- Train an XGBoost regressor to predict future prices
- Evaluate model performance using statistical metrics

## Results
- **Sentiment Analysis Findings**:
  - Identifies shifts in market sentiment based on financial news.
  - Visualizations help interpret sentiment distribution over time.
- **XGBoost Model Performance**:
  - Achieves high accuracy in short-term price predictions.
  - Shows correlation between sentiment shifts and price movements.
- **Key Insights**:
  - Combining sentiment scores with historical price data improves prediction reliability.
  - Volatility in sentiment scores often correlates with sudden price changes.

## Future Improvements
- Expand data sources to include social media sentiment (e.g., Twitter, Reddit).
- Implement real-time sentiment tracking and live price forecasting.
- Explore deep learning techniques (e.g., LSTMs, Transformers) for improved accuracy.
- Develop a web dashboard for interactive visualization of sentiment trends and price predictions.

## License
This project is licensed under the MIT License.


