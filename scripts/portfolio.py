import pandas as pd
import json
import os
import yfinance as yf
from datetime import datetime

PORTFOLIO_FILE = "data/portfolio.json"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE) as f:
            return json.load(f)
    return []

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=2)

def add_buy(ticker, shares, buy_date, buy_price=None):
    portfolio = load_portfolio()
    
    # If no price given, fetch the actual price on that date
    if buy_price is None:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=buy_date, end=buy_date)
        if hist.empty:
            hist = stock.history(start=buy_date, period="5d")
        buy_price = round(hist["Close"].iloc[0], 2) if not hist.empty else None

    if buy_price is None:
        print(f"Could not find price for {ticker} on {buy_date}")
        return

    entry = {
        "ticker":    ticker.upper(),
        "shares":    shares,
        "buy_date":  buy_date,
        "buy_price": buy_price,
        "cost":      round(shares * buy_price, 2)
    }
    portfolio.append(entry)
    save_portfolio(portfolio)
    print(f"Added: {shares} shares of {ticker} at ${buy_price} on {buy_date}")
    print(f"Total cost: ${entry['cost']}")

def show_portfolio():
    portfolio = load_portfolio()
    if not portfolio:
        print("No positions yet. Use add_buy() to add one.")
        return

    print("\n===== PORTFOLIO =====\n")
    print(f"{'Ticker':<8} {'Shares':<8} {'Buy Date':<12} {'Buy $':<10} {'Now $':<10} {'Gain $':<12} {'Gain %':<10} {'Value'}")
    print("-" * 85)

    total_cost  = 0
    total_value = 0

    for entry in portfolio:
        ticker    = entry["ticker"]
        shares    = entry["shares"]
        buy_price = entry["buy_price"]
        buy_date  = entry["buy_date"]
        cost      = entry["cost"]

        # Get current price
        try:
            stock = yf.Ticker(ticker)
            now_price = stock.info.get("currentPrice") or stock.fast_info["last_price"]
            now_price = round(now_price, 2)
        except:
            now_price = buy_price

        value    = round(shares * now_price, 2)
        gain     = round(value - cost, 2)
        gain_pct = round((gain / cost) * 100, 2)

        total_cost  += cost
        total_value += value

        arrow = "▲" if gain >= 0 else "▼"
        print(f"{ticker:<8} {shares:<8} {buy_date:<12} ${buy_price:<9} ${now_price:<9} {arrow}${abs(gain):<10} {arrow}{abs(gain_pct)}%{'':<4} ${value}")

    total_gain     = round(total_value - total_cost, 2)
    total_gain_pct = round((total_gain / total_cost) * 100, 2)
    arrow = "▲" if total_gain >= 0 else "▼"

    print("-" * 85)
    print(f"{'TOTAL':<8} {'':<8} {'':<12} ${total_cost:<9} {'':<10} {arrow}${abs(total_gain):<10} {arrow}{abs(total_gain_pct)}%{'':<4} ${total_value}")

    # Save summary to CSV
    rows = []
    for entry in portfolio:
        ticker = entry["ticker"]
        try:
            stock = yf.Ticker(ticker)
            now_price = round(stock.info.get("currentPrice") or stock.fast_info["last_price"], 2)
        except:
            now_price = entry["buy_price"]
        value    = round(entry["shares"] * now_price, 2)
        gain     = round(value - entry["cost"], 2)
        gain_pct = round((gain / entry["cost"]) * 100, 2)
        rows.append({**entry, "now_price": now_price, "value": value, "gain": gain, "gain_pct": gain_pct})
    
    pd.DataFrame(rows).to_csv("data/portfolio_performance.csv", index=False)
    print("\nSaved to data/portfolio_performance.csv")

if __name__ == "__main__":
    # Example: add some hypothetical buys then show performance
    # Comment these out after first run and just call show_portfolio()
    
    add_buy("AAPL", 10, "2024-01-01")
    add_buy("MSFT", 5,  "2024-01-01")
    add_buy("NVDA", 8,  "2024-01-01")
    add_buy("META", 6,  "2024-06-01")
    
    show_portfolio()
