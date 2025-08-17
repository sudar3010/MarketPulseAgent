# AI News Agent POC

This project automates the detection and summarization of material news events — earnings, management changes, and regulatory probes — for Indian equities.

## 🔍 Features
- Detects key events using Google News RSS,News api
- Summarizes headlines using AI prompt engineering
- Filters for thesis-changing signals
- Delivers updates to Telegram via GitHub Actions

## 🛠️ Tech Stack
- Python
- GitHub Actions
- Telegram Bot API
- RSS Parsing
- Prompt Engineering

  ## 🔐 Secrets & Configuration

This repo uses GitHub Actions and requires the following secrets to be set in the repository:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `NEWS_API_KEY`: API key for news source (e.g., GNEWS_API_KEY, NewsAPI,RAPIDAPI_KEY for price)
- `STOCK_LIST`: Comma-separated list of stock tickers to monitor

> ⚠️ This project is for **showcase purposes only**. Secrets are used to demonstrate automation and modular design, not for production use.

## 🚀 How to Run
1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Configure your Telegram bot token and stock list
4. Run: `python main.py`

## 📈 Roadmap
- Add multi-source event detection
- Improve summarization quality
- Test new message styles for engagement

## 📄 License
MIT License
