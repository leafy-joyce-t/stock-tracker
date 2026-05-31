import yfinance as yf
import pandas as pd
import os
from datetime import datetime

WATCHLIST = ["AAPL", "MSFT", "JNJ", "KO", "V"]

def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    return {
        "ticker": ticker,
        "date": datetime.today().strftime("%Y-%m-%d"),
        "price": info.get("currentPrice"),
        "pe_ratio": info.get("trailingPE"),
        "roe": info.get("returnOnEquity"),
        "free_cash_flow": info.get("freeCashflow"),
        "debt_to_equity": info.get("debtToEquity"),
        "revenue_growth": info.get("revenueGrowth"),
        "profit_margin": info.get("profitMargins"),
        "dividend_yield": info.get("dividendYield"),
    }

def main():
    os.makedirs("data", exist_ok=True)
    results = []
    for ticker in WATCHLIST:
        print(f"Fetching {ticker}...")
        data = fetch_stock_data(ticker)
        results.append(data)
    df = pd.DataFrame(results)
    df.to_csv("data/metrics.csv", index=False)
    print("\nDone! Saved to data/metrics.csv")
    print(df.to_string())

if __name__ == "__main__":
    main()
