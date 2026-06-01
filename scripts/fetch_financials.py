import yfinance as yf
import json
import os

def load_watchlist():
    wl = []
    port = []
    if os.path.exists("data/watchlist.json"):
        wl = json.load(open("data/watchlist.json"))
    if os.path.exists("data/portfolio.json"):
        port = json.load(open("data/portfolio.json"))
    return list(set(wl + [e["ticker"] for e in port]))

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
    WATCHLIST = load_watchlist()
    print(f"Fetching {len(WATCHLIST)} tickers: {WATCHLIST}")
    for ticker in WATCHLIST:
        print(f"Fetching {ticker}...")
        try:
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
        except Exception as e:
            print(f"  Error {ticker}: {e}")
    print("Done!")

if __name__ == "__main__":
    main()
