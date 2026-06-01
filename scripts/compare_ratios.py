import requests
import pandas as pd
import re
import json
import os
from bs4 import BeautifulSoup

import json as _json
def _load_watchlist():
    try:
        wl = _json.load(open("data/watchlist.json"))
        port = _json.load(open("data/portfolio.json")) if os.path.exists("data/portfolio.json") else []
        port_tickers = [e["ticker"] for e in port]
        return list(set(wl + port_tickers))
    except:
        return ["AAPL", "MSFT", "META", "NVDA"]
WATCHLIST = _load_watchlist()
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

NAME_MAP = {
    "AAPL": "apple", "MSFT": "microsoft", "META": "meta-platforms",
    "NVDA": "nvidia", "MRNA": "moderna", "NET": "cloudflare",
    "RBLX": "roblox", "HOOD": "robinhood-markets", "LMND": "lemonade",
    "SNDK": "sandisk"
}

def get_finviz(ticker):
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "lxml")
        cells = soup.find_all("td", class_="snapshot-td2")
        labels = soup.find_all("td", class_="snapshot-td2-cp")
        data = {l.text.strip(): c.text.strip() for l, c in zip(labels, cells)}
        return {
            "finviz_pe":     data.get("P/E", "N/A"),
            "finviz_roe":    data.get("ROE", "N/A"),
            "finviz_margin": data.get("Profit M", "N/A"),
            "finviz_de":     data.get("Debt/Eq", "N/A"),
        }
    except Exception as e:
        print(f"  Finviz error for {ticker}: {e}")
        return {"finviz_pe": "N/A", "finviz_roe": "N/A", "finviz_margin": "N/A", "finviz_de": "N/A"}

def get_macrotrends_pe(ticker):
    try:
        name = NAME_MAP.get(ticker, ticker.lower())
        url = f"https://www.macrotrends.net/stocks/charts/{ticker}/{name}/pe-ratio"
        r = requests.get(url, headers=HEADERS, timeout=10)
        match = re.search(r'var originalData = (\[.*?\]);', r.text, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            if data:
                return {"macrotrends_pe": data[-1].get("v", "N/A")}
        return {"macrotrends_pe": "N/A"}
    except Exception as e:
        print(f"  Macrotrends error for {ticker}: {e}")
        return {"macrotrends_pe": "N/A"}

def main():
    os.makedirs("data", exist_ok=True)
    try:
        our = pd.read_csv("data/calculated_ratios.csv")
        scores = pd.read_csv("data/scores.csv")
    except FileNotFoundError:
        print("Run calculate_ratios.py and score_stocks.py first!")
        return

    results = []
    for ticker in WATCHLIST:
        print(f"Comparing {ticker}...")
        row = {"ticker": ticker}

        our_row = our[our["ticker"] == ticker]
        score_row = scores[scores["ticker"] == ticker]

        if not our_row.empty:
            row["our_pe"]     = our_row["pe_ratio"].values[0]
            row["our_roe"]    = our_row["roe"].values[0]
            row["our_margin"] = our_row["profit_margin"].values[0]

        if not score_row.empty:
            row["score"]  = score_row["score"].values[0]
            row["rating"] = score_row["rating"].values[0]

        row.update(get_finviz(ticker))
        row.update(get_macrotrends_pe(ticker))
        results.append(row)

    df = pd.DataFrame(results).sort_values("score", ascending=False)
    df.to_csv("data/comparison.csv", index=False)

    print("\n===== RATIO COMPARISON =====\n")
    print(f"{'Ticker':<6} {'Score':<7} {'Rating':<12} {'Our P/E':<10} {'Finviz P/E':<12} {'MT P/E':<10} {'Our ROE':<10} {'Finviz ROE'}")
    print("-" * 80)
    for _, r in df.iterrows():
        print(f"{r['ticker']:<6} {str(r.get('score','')):<7} {str(r.get('rating','')):<12} {str(round(r['our_pe'],1) if pd.notna(r.get('our_pe')) else 'N/A'):<10} {str(r.get('finviz_pe','')):<12} {str(r.get('macrotrends_pe','')):<10} {str(round(r['our_roe'],3) if pd.notna(r.get('our_roe')) else 'N/A'):<10} {str(r.get('finviz_roe',''))}")

    print("\nSaved to data/comparison.csv")

if __name__ == "__main__":
    main()
