import yfinance as yf
import pandas as pd
import json
import os

def get_risk_signals(ticker):
    stock   = yf.Ticker(ticker)
    info    = stock.info
    hist    = stock.history(period="6mo")
    risks   = []
    bonus   = []
    penalty = 0
    boost   = 0

    if len(hist) >= 60:
        price_now = hist["Close"].iloc[-1]
        price_3m  = hist["Close"].iloc[-63] if len(hist) >= 63 else hist["Close"].iloc[0]
        price_6m  = hist["Close"].iloc[0]
        mom_3m = (price_now - price_3m) / price_3m * 100
        mom_6m = (price_now - price_6m) / price_6m * 100
        if mom_3m < -15:
            penalty += 15
            risks.append("Down in 3 months (-15)")
        elif mom_3m < -5:
            penalty += 8
            risks.append("Down in 3 months (-8)")
        elif mom_3m > 15:
            boost += 8
            bonus.append("Up in 3 months (+8)")
        if mom_6m < -25:
            penalty += 10
            risks.append("Down in 6 months (-10)")
        elif mom_6m > 25:
            boost += 5
            bonus.append("Up in 6 months (+5)")

    short_pct = info.get("shortPercentOfFloat")
    if short_pct:
        if short_pct > 0.20:
            penalty += 12
            risks.append("High short interest (-12)")
        elif short_pct > 0.10:
            penalty += 6
            risks.append("Elevated short interest (-6)")
        elif short_pct < 0.03:
            boost += 5
            bonus.append("Low short interest (+5)")

    insider_own = info.get("heldPercentInsiders")
    if insider_own:
        if insider_own > 0.10:
            boost += 8
            bonus.append("High insider ownership (+8)")
        elif insider_own < 0.01:
            penalty += 5
            risks.append("Low insider ownership (-5)")

    rev_growth      = info.get("revenueGrowth")
    earnings_growth = info.get("earningsGrowth")
    if rev_growth and earnings_growth:
        if rev_growth < 0 and earnings_growth < 0:
            penalty += 15
            risks.append("Revenue and earnings shrinking (-15)")
        elif rev_growth < 0:
            penalty += 8
            risks.append("Revenue declining (-8)")

    peg = info.get("pegRatio")
    if peg:
        if peg > 3:
            penalty += 10
            risks.append("PEG overvalued vs growth (-10)")
        elif peg > 2:
            penalty += 5
            risks.append("PEG stretched (-5)")
        elif 0 < peg < 1:
            boost += 10
            bonus.append("PEG undervalued vs growth (+10)")

    price    = info.get("currentPrice")
    low_52w  = info.get("fiftyTwoWeekLow")
    high_52w = info.get("fiftyTwoWeekHigh")
    if price and low_52w and high_52w and high_52w > low_52w:
        pct = (price - low_52w) / (high_52w - low_52w)
        if pct > 0.90:
            penalty += 8
            risks.append("Near 52-week high (-8)")
        elif pct < 0.20:
            boost += 8
            bonus.append("Near 52-week low (+8)")

    return {
        "ticker":      ticker,
        "penalty":     penalty,
        "boost":       boost,
        "risk_flags":  str(risks),
        "bonus_flags": str(bonus),
        "net":         boost - penalty,
    }

def main():
    wl   = json.load(open("data/watchlist.json")) if os.path.exists("data/watchlist.json") else []
    port = json.load(open("data/portfolio.json"))  if os.path.exists("data/portfolio.json")  else []
    tickers = list(set(wl + [e["ticker"] for e in port]))
    print("Analyzing " + str(len(tickers)) + " tickers...")
    results = []
    for ticker in tickers:
        print("  " + ticker)
        try:
            results.append(get_risk_signals(ticker))
        except Exception as e:
            print("    Error: " + str(e))
    pd.DataFrame(results).to_csv("data/risk_signals.csv", index=False)
    print("Done!")

if __name__ == "__main__":
    main()

    