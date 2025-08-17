import os
import time
import requests
import urllib.parse
from datetime import datetime, timedelta, timezone
import pytz
import google.generativeai as genai
from dateutil import parser
from config.settings import  PRICE_API_HEADERS

# === CONFIG ===
SYMBOLS = ["TCS"]

# 🔑 API Keys
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "b31ee22f579e68f9801f182b9217b962")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "3ae1e0aeff514f348eb78a8101af020c")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8108841318:AAE8aoEPqOU6SrwzRvtAjOQAG9AjD2IT2NI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002786819893")

# Gemini Config
genai.configure(api_key=os.getenv("GEMINI_API_KEY", "AIzaSyAolmRW2NKcmqd83Z-lnLp2oyNiocSm3c8"))

# === STOCK KEYWORDS ===
STOCK_KEYWORDS = [
    "stock", "share", "market", "nse", "bse", "sensex", "nifty",
    "results", "earnings", "profit", "revenue", "quarter", "q1", "q2", "q3", "q4",
    "dividend", "buyback", "ipo", "contract", "deal", "acquisition", "merger"
]

def is_stock_related(title, desc):
    text = f"{title} {desc}".lower()
    return any(keyword in text for keyword in STOCK_KEYWORDS)

# === Fetch News (GNews + NewsAPI fallback) ===
def fetch_from_gnews(symbol, days=3):
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
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": NEWSAPI_KEY
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
PRICE_API_HEADERS = {
    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY", "701d4da0e2msh9fb6b21538296c5p1e194fjsn9e4ee7a6c936"),
    "X-RapidAPI-Host": "indian-stock-exchange-api2.p.rapidapi.com"
}
# === Generate Combined Summary ===
def generate_summary(symbol):
   def process_stock(symbol):
    print(f"\nProcessing {symbol}...")
    
    # === PRICE API CALL ===
    price_api_url = f"https://indian-stock-exchange-api2.p.rapidapi.com/stock?name={symbol}"
    price_resp = requests.get(price_api_url, headers=PRICE_API_HEADERS)
    price_data = price_resp.json()
    
    # === Extract company info ===
    company_info = None
    peer_companies = []
    if "peerCompanyList" in price_data:
        peer_companies = price_data["peerCompanyList"]
    elif "companyProfile" in price_data and "peerCompanyList" in price_data["companyProfile"]:
        peer_companies = price_data["companyProfile"]["peerCompanyList"]
    elif "stockDetailsReusableData" in price_data and "peerCompanyList" in price_data["stockDetailsReusableData"]:
        peer_companies = price_data["stockDetailsReusableData"]["peerCompanyList"]
    SYMBOL_NAME_MAP = {
    "KTKBANK": "Karnataka Bank",
    "TCS": "Tata Consultancy Services",
    # Add more special cases if needed
}
    for company in peer_companies:
     company_name = company.get("companyName", "").lower()
    
    # If symbol is in special mapping, match by mapped name
     if symbol.upper() in SYMBOL_NAME_MAP:
        if SYMBOL_NAME_MAP[symbol.upper()].lower() in company_name:
            company_info = company
            break
     else:
        # Normal case: match by symbol in name
        if symbol.lower() in company_name:
            company_info = company
            break

    # === Extract news content ===
    news_content = ""
    if company_info:
        news_content += (
            f"{company_info['companyName']}:\n"
            f"Current Price: ₹{company_info['price']}\n"
            f"52 Week High: ₹{company_info['yhigh']}\n"
            f"52 Week Low: ₹{company_info['ylow']}\n\n"
        )
    try:
        investor_notes = []
        score = 50  # Start from neutral
        max_score = 100
        min_score = 0

        # === BASIC DATA EXTRACTION ===
        price = float(company_info.get("price", 0))
        yhigh = float(company_info.get("yhigh", 0))
        ylow = float(company_info.get("ylow", 0))
        pe = float(company_info.get("priceToEarningsValueRatio", 0))
        pb = float(company_info.get("priceToBookValueRatio", 0))
        roe = float(company_info.get("returnOnAverageEquityTrailing12Month", 0))
        net_margin = float(company_info.get("netProfitMarginPercentTrailing12Month", 0))
        dividend_yield = float(company_info.get("dividendYieldIndicatedAnnualDividend", 0))
        debt_to_equity = float(company_info.get("ltDebtPerEquityMostRecentFiscalYear", 0))
        rating = company_info.get("overallRating", "").capitalize()
        percent_change = float(company_info.get("percentChange", 0))

        # === LONG-TERM FUNDAMENTAL METRICS ===
        eps_growth_5yr = 0.0
        growth_data = price_data.get("keyMetrics", {}).get("growth", [])
        for item in growth_data:
          if item.get("key") == "ePSGrowthRate5Year":
             eps_growth_5yr = float(item.get("value", 0))
             break
        print("EPS Growth Rate (5Y):", eps_growth_5yr)

# === Revenue Growth Rate (5 Year) ===
        revenue_growth = 0.0
        for item in growth_data:
          if item.get("key") == "revenueGrowthRate5Year":
             revenue_growth = float(item.get("value", 0))
             break

# === PEG Ratio (inside keyMetrics -> valuation) ===
        peg_ratio = 0.0
        valuation_data = price_data.get("keyMetrics", {}).get("valuation", [])
        for item in valuation_data:
          if item.get("key") == "pegRatio":
            peg_ratio = float(item.get("value", 0))
            break

# === Dividend Growth (3 Year) (inside keyMetrics -> growth) ===
        dividend_growth_5y = 0.0
        for item in growth_data:
         if item.get("key") == "growthRatePercentDividend3Year":
            dividend_growth_5y = float(item.get("value", 0))
            break

# === Free Cash Flow TTM (inside keyMetrics -> financialstrength) ===
        fcf_yield = 0.0
        financial_strength_data = price_data.get("keyMetrics", {}).get("financialstrength", [])
        for item in financial_strength_data:
           if item.get("key") == "freeCashFlowtrailing12Month":
              fcf_yield = float(item.get("value", 0))
              break

# === Beta (inside keyMetrics -> priceandvolume) ===
        beta = 0.0
        price_volume_data = price_data.get("keyMetrics", {}).get("priceandVolume", [])
        for item in price_volume_data:
           if item.get("key") == "beta":
              try:
                 beta_str = str(item.get("value", "0")).replace(",", ".")
                 beta = float(beta_str)
              except ValueError:
                 beta = 0.0
              break




        # === VALUATION SIGNALS ===
        if pe < 8 and pb < 1:
            investor_notes.append("💰 Potential Value Buy — Low P/E & P/B suggest undervaluation")
            score += 6
        elif pe > 25 and pb > 4:
            investor_notes.append("⚠️ Overvalued — High P/E & P/B")
            score -= 6

        if 0 < peg_ratio < 1:
            investor_notes.append("📉 Undervalued vs. Growth — PEG < 1")
            score += 5

        # === PROFITABILITY ===
        if roe > 10 and net_margin > 20:
            investor_notes.append("📈 Strong Profitability — High ROE & Net Margin")
            score += 6
        elif roe < 5:
            investor_notes.append("⚠️ Weak Profitability — Low ROE")
            score -= 4

        # === DIVIDEND ===
        if dividend_yield > 2:
            investor_notes.append(f"💵 Good Dividend Yield ({dividend_yield:.2f}%)")
            score += 4
        if dividend_growth_5y > 5:
            investor_notes.append(f"💵 Consistent Dividend Growth ({dividend_growth_5y:.2f}% CAGR)")
            score += 3

        # === FINANCIAL HEALTH ===
        if debt_to_equity > 2 and "bank" not in company_info.get("companyName", "").lower():
            investor_notes.append(f"⚠️ High Leverage Risk — Debt/Equity: {debt_to_equity:.2f}")
            score -= 6
        elif debt_to_equity < 0.5:
            investor_notes.append(f"🛡️ Strong Balance Sheet — Low Debt/Equity ({debt_to_equity:.2f})")
            score += 3

        if fcf_yield > 5:
            investor_notes.append(f"💡 High Free Cash Flow Yield ({fcf_yield:.2f}%) — Strong Liquidity")
            score += 4

        # === GROWTH ===
        if eps_growth_5yr > 10:
            investor_notes.append(f"🚀 Strong Earnings Growth ({eps_growth_5yr:.2f}% CAGR over 5Y)")
            score += 5
        elif eps_growth_5yr < 0:
            investor_notes.append(f"⚠️ Negative Earnings Growth ({eps_growth_5yr:.2f}%)")
            score -= 6

        if revenue_growth > 8:
            investor_notes.append(f"📊 Healthy Revenue Growth ({revenue_growth:.2f}%)")
            score += 4

        # === VOLATILITY ===
        if beta < 0.8:
            investor_notes.append(f"🛡️ Low Volatility (Beta: {beta:.2f}) — Defensive Play")
            score += 3
        elif beta > 1.5:
            investor_notes.append(f"⚡ High Volatility Risk (Beta: {beta:.2f})")
            score -= 3

        

        # === PRICE POSITION ===
        if ylow > 0 and ((price - ylow) / ylow) * 100 < 5:
            investor_notes.append("📉 Near 52-Week Low — Possible Value Entry")
            score += 2
        if price > 0 and ((yhigh - price) / price) * 100 < 5:
            investor_notes.append("📊 Near 52-Week High — Consider Profit Booking")
            score -= 2

        # === SENTIMENT ===
        if rating:
            sentiment_emoji = "📈" if rating.lower() == "bullish" else "📉" if rating.lower() == "bearish" else "⚖️"
            investor_notes.append(f"{sentiment_emoji} Market Sentiment: {rating}")
            score += 2 if rating.lower() == "bullish" else -2 if rating.lower() == "bearish" else 0

        if percent_change <= -3:
            investor_notes.append(f"🔻 Significant Drop Today ({percent_change:.2f}%) — Review Position")
            score -= 1


        # === FINAL SCORE RANGE ===
        # score = max(min_score, min(max_score, score))
        # investor_notes.append(f"📊 **Long-Term Attractiveness Score:** {score}/100")

    except Exception as e:
        print(f"⚠️ Error generating investor notes: {e}")
    
    # --- News Fetch ---
    articles = fetch_from_gnews(symbol)
    if not articles:
        articles = fetch_from_newsapi(symbol)

    if not articles:
        return f"📭 No stock-related news in the past 2 days for {symbol}.\n{investor_notes}"

    article = articles[0]
    raw = f"- {article['title']}\n  {article['desc']}\n  🔗 {article['url']}"

    prompt = f"""
You are a financial news explainer. Summarize this news about {symbol} in **fixed format** in layman language:

**Stock Update** (📈 Positive/Bullish, 📉 Negative/Bearish, ⚖️ Neutral)
- Clear stock/company news. Else: "No latest news"

**Sector Trend** (📈 / 📉 / ⚖️)
- Broader sector trend. Else: "No latest news"

**Reasons/Drivers** (📈 / 📉 / ⚖️)
- Reasons like demand, regulation, global trends. Else: "No latest news"

**Result** (📈 / 📉 / ⚖️)
- Quarterly/annual results. Else: "No latest news"

**Promoter / Big Sell / Acquisition** (📈 / 📉 / ⚖️)
- Promoter selling, big deals, acquisitions. Else: "No latest news"

Do not add extra explanation.

News:
{raw}

📅 Date Published: {article['date']}
"""
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    return f"{investor_notes}\n📰 {article['date']}\n{response.text}"

# === Telegram Sender ===
def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    resp = requests.post(url, data=payload)
    return resp.status_code == 200

# === Main Runner ===
if __name__ == "__main__":
    for symbol in SYMBOLS:
        print(f"🔄 Processing {symbol}")
        summary = generate_summary(symbol)
        print(summary)
        send_to_telegram(summary)
        time.sleep(15)
