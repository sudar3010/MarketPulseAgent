import requests
import os
from datetime import datetime, timedelta, timezone
import google.generativeai as genai

# 🔑 API Keys
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "b31ee22f579e68f9801f182b9217b962")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "3ae1e0aeff514f348eb78a8101af020c")
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAolmRW2NKcmqd83Z-lnLp2oyNiocSm3c8"))

# ✅ Stock/finance related keywords
STOCK_KEYWORDS = [
    "stock", "share", "market", "nse", "bse", "sensex", "nifty",
    "results", "earnings", "profit", "revenue", "quarter", "q1", "q2", "q3", "q4",
    "dividend", "buyback", "ipo", "contract", "deal", "acquisition", "merger"
]

def is_stock_related(title, desc):
    text = f"{title} {desc}".lower()
    return any(keyword in text for keyword in STOCK_KEYWORDS)

def fetch_from_gnews(symbol, days=5):
    url = f"https://gnews.io/api/v4/search?q={symbol}&lang=en&country=in&max=10&token={GNEWS_API_KEY}"
    resp = requests.get(url).json()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    articles = []
    for a in resp.get("articles", []):
        try:
            pub_date = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
        except:
            continue

        if pub_date >= cutoff and is_stock_related(a.get("title", ""), a.get("description", "")):
            articles.append({
                "title": a.get("title", ""),
                "desc": a.get("description", ""),
                "url": a.get("url", ""),
                "date": pub_date.strftime("%Y-%m-%d")
            })
    return articles

def fetch_from_newsapi(symbol, days=2):
    base = "https://newsapi.org/v2/everything"
    to_date = datetime.now(timezone.utc)
    params = {
        "q": f'"{symbol}" OR "{symbol} company India"',
        "from": (to_date - timedelta(days=days)).strftime("%Y-%m-%d"),
        "to": to_date.strftime("%Y-%m-%d"),
        "sortBy": "publishedAt", "language": "en", "apiKey": NEWSAPI_KEY
    }
    resp = requests.get(base, params=params)
    data = resp.json()

    articles = []
    for a in data.get("articles", []):
        if is_stock_related(a.get("title", ""), a.get("description", "")):
            articles.append({
                "title": a.get("title", ""),
                "desc": a.get("description", ""),
                "url": a.get("url", ""),
                "date": a["publishedAt"][:10]
            })
    return articles

def generate_summary(symbol):
    articles = fetch_from_gnews(symbol)
    if not articles:
        articles = fetch_from_newsapi(symbol)

    if not articles:
        return f"📭 No stock-related news in the past 2 days for {symbol}."

    article = articles[0]  # Take the latest relevant one
    raw = f"- {article['title']}\n  {article['desc']}\n  🔗 {article['url']}"

    # Structured prompt with strict fallback rules
    prompt = f"""
You are a financial news explainer. Summarize this news about {symbol} in the following **fixed format** in simple layman language (avoid complex business/financial jargon):

**Stock Update** (📈 Positive/Bullish, 📉 Negative/Bearish, ⚖️ Neutral)
- If there is clear stock/company-specific news (earnings, results, price move, contract, merger etc.), write 1–2 bullets in layman language.
- If not, write exactly: "No latest news"

**Sector Trend** (📈 / 📉 / ⚖️)
- If the article mentions the broader industry/sector trend, write 1–2 bullets in layman language.
- If not, write exactly: "No latest news"

**Reasons/Drivers** (📈 / 📉 / ⚖️)
- If reasons are given (demand, regulation, global trends, market factors), write 1–2 bullets in layman language.
- If not, write exactly: "No latest news"

**Result** (📈 / 📉 / ⚖️)
- If quarterly or annual results are mentioned, summarize 1–2 points in layman language.
- If not, write exactly: "No latest news"

**Promoter / Big Sell / Acquisition** (📈 / 📉 / ⚖️)
- If promoters sold stake, big investors exited/entered, or company announced an acquisition/sell-off, mention in 1–2 points.
- If not, write exactly: "No latest news"

Do not add extra explanation outside this structure.

News:
{raw}

📅 Date Published: {article['date']}
"""


    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    return f"📰 {article['date']}\n{response.text}"

if __name__ == "__main__":
    print(generate_summary("Genesys International"))
