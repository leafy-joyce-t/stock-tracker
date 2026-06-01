import yfinance as yf
import pandas as pd
import json
import os

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

def get_statements(ticker):
    stock = yf.Ticker(ticker)
    return {
        "income":   stock.financials,
        "balance":  stock.balance_sheet,
        "cashflow": stock.cashflow,
        "price":    stock.info.get("currentPrice"),
        "shares":   stock.info.get("sharesOutstanding"),
    }

def main():
    os.makedirs("data/financials", exist_ok=True)
    for ticker in WATCHLIST:
        print(f"Fetching {ticker}...")
        data = get_statements(ticker)
        if data["income"] is not None:
            data["income"].to_csv(f"data/financials/{ticker}_income.csv")
        if data["balance"] is not None:
            data["balance"].to_csv(f"data/financials/{ticker}_balance.csv")
        if data["cashflow"] is not None:
            data["cashflow"].to_csv(f"data/financials/{ticker}_cashflow.csv")
        with open(f"data/financials/{ticker}_info.json", "w") as f:
            json.dump({"price": data["price"], "shares": data["shares"]}, f)
        print(f"  Saved {ticker}")
    print("\nDone! Raw financials saved to data/financials/")

if __name__ == "__main__":
    main()
