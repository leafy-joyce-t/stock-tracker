import yfinance as yf
import pandas as pd
import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from risk_signals import get_risk_signals

UNIVERSE = [
    # Tech
    "AAPL","MSFT","GOOGL","META","NVDA","AMD","INTC","CRM","ADBE","ORCL",
    "CSCO","IBM","QCOM","TXN","NOW","SNOW","PLTR","UBER","LYFT","NET",
    # Finance
    "JPM","BAC","WFC","GS","MS","BLK","V","MA","PYPL","AXP",
    "SCHW","C","USB","PNC","TFC","HOOD","SOFI","COF","AMP","MET",
    # Healthcare
    "JNJ","UNH","PFE","ABBV","MRK","TMO","ABT","DHR","BMY","AMGN",
    "GILD","ISRG","SYK","BSX","MDT","MRNA","REGN","VRTX","BIIB","HCA",
    # Consumer
    "AMZN","WMT","COST","TGT","HD","LOW","MCD","SBUX","NKE","LULU",
    "YUM","DPZ","CMG","ROST","TJX","DLTR","KO","PEP","PM","MO",
    # Energy
    "XOM","CVX","COP","SLB","EOG","PXD","MPC","VLO","PSX","OXY",
    # Industrial
    "CAT","DE","HON","UPS","FDX","LMT","RTX","BA","GE","MMM",
    # Real Estate / Utilities
    "AMT","PLD","EQIX","O","SPG","NEE","DUK","SO","AEP","EXC",
    # Other
    "TSLA","BRK-B","DIS","NFLX","SPOT","RBLX","LMND","SNDK","NKE","AME"
]

def load_watchlist():
    wl   = json.load(open("data/watchlist.json")) if os.path.exists("data/watchlist.json") else []
    port = json.load(open("data/portfolio.json"))  if os.path.exists("data/portfolio.json")  else []
    return list(set(wl + [e["ticker"] for e in port]))

def score_fundamentals(info):
    score = 0
    reasons = []

    pe = info.get("trailingPE")
    if pe and pe > 0:
        if pe < 15:   score += 15; reasons.append("P/E under 15")
        elif pe < 25: score += 10; reasons.append("P/E under 25")
        elif pe < 35: score += 5;  reasons.append("P/E under 35")

    roe = info.get("returnOnEquity")
    if roe:
        if roe > 0.30:   score += 15; reasons.append("ROE over 30%")
        elif roe > 0.15: score += 10; reasons.append("ROE over 15%")
        elif roe > 0:    score += 5;  reasons.append("ROE positive")

    fcf = info.get("freeCashflow")
    if fcf:
        if fcf > 1_000_000_000: score += 15; reasons.append("FCF over $1B")
        elif fcf > 0:            score += 10; reasons.append("FCF positive")

    de = info.get("debtToEquity")
    if de:
        if de < 50:    score += 15; reasons.append("Low debt")
        elif de < 100: score += 10; reasons.append("Moderate debt")
        elif de < 200: score += 5;  reasons.append("Manageable debt")

    margin = info.get("profitMargins")
    if margin:
        if margin > 0.20:   score += 15; reasons.append("Margin over 20%")
        elif margin > 0.10: score += 10; reasons.append("Margin over 10%")
        elif margin > 0:    score += 5;  reasons.append("Margin positive")

    growth = info.get("revenueGrowth")
    if growth:
        if growth > 0.20:   score += 10; reasons.append("Revenue growth over 20%")
        elif growth > 0.10: score += 7;  reasons.append("Revenue growth over 10%")
        elif growth > 0:    score += 3;  reasons.append("Revenue growth positive")

    return score, reasons

def main():
    os.makedirs("data", exist_ok=True)
    tracked = load_watchlist()
    results = []

    print("Screening " + str(len(UNIVERSE)) + " stocks...")
    for ticker in UNIVERSE:
        if ticker in tracked:
            continue
        try:
            stock = yf.Ticker(ticker)
            info  = stock.info
            price = info.get("currentPrice")
            name  = info.get("shortName", ticker)
            if not price:
                continue

            # Fundamental score
            fund_score, fund_reasons = score_fundamentals(info)

            # Risk signals
            risk = get_risk_signals(ticker)
            penalty     = risk.get("penalty", 0)
            boost       = risk.get("boost", 0)
            risk_flags  = risk.get("risk_flags", "[]")
            bonus_flags = risk.get("bonus_flags", "[]")

            final_score = max(0, fund_score - penalty + boost)

            import ast
            try:
                rf = ast.literal_eval(risk_flags)  if isinstance(risk_flags,  str) else []
                bf = ast.literal_eval(bonus_flags) if isinstance(bonus_flags, str) else []
            except:
                rf = []; bf = []

            all_reasons = fund_reasons + bf + ["⚠️ " + r for r in rf]

            results.append({
                "ticker":   ticker,
                "name":     name,
                "price":    price,
                "sector":   info.get("sector", "Other"),
                "score":    final_score,
                "pe":       round(info.get("trailingPE", 0) or 0, 1),
                "roe":      round((info.get("returnOnEquity") or 0) * 100, 1),
                "margin":   round((info.get("profitMargins") or 0) * 100, 1),
                "growth":   round((info.get("revenueGrowth") or 0) * 100, 1),
                "peg":      round(info.get("pegRatio") or 0, 2),
                "reasons":  " | ".join(all_reasons),
            })
            print("  " + ticker + ": " + str(final_score) + "/95")
        except Exception as e:
            print("  " + ticker + " error: " + str(e))

    df = pd.DataFrame(results).sort_values("score", ascending=False)
    df.to_csv("data/screener.csv", index=False)
    print("Done! Top 10:")
    for _, row in df.head(10).iterrows():
        print("  " + row["ticker"] + "  " + str(row["score"]) + "/95  $" + str(row["price"]))

if __name__ == "__main__":
    main()