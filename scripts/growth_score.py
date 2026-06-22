import pandas as pd
import json
import os

def load_watchlist():
    wl = json.load(open("data/watchlist.json")) if os.path.exists("data/watchlist.json") else []
    port = json.load(open("data/portfolio.json")) if os.path.exists("data/portfolio.json") else []
    return list(set(wl + [e["ticker"] for e in port]))

def score_growth(info):
    score = 0
    reasons = []

    growth = info.get("revenueGrowth")
    if growth:
        if growth > 0.50:
            score += 25
            reasons.append("Explosive revenue growth over 50% (+25)")
        elif growth > 0.30:
            score += 20
            reasons.append("Strong revenue growth over 30% (+20)")
        elif growth > 0.15:
            score += 12
            reasons.append("Solid revenue growth over 15% (+12)")
        elif growth > 0:
            score += 5
            reasons.append("Positive revenue growth (+5)")
        else:
            reasons.append("Revenue shrinking (0)")

    earn_growth = info.get("earningsGrowth")
    if earn_growth:
        if earn_growth > 0.30:
            score += 15
            reasons.append("Strong earnings growth over 30% (+15)")
        elif earn_growth > 0.10:
            score += 8
            reasons.append("Earnings growth over 10% (+8)")
        elif earn_growth > 0:
            score += 3
            reasons.append("Earnings growth positive (+3)")

    price = info.get("currentPrice")
    low_52w = info.get("fiftyTwoWeekLow")
    high_52w = info.get("fiftyTwoWeekHigh")
    if price and low_52w and high_52w and high_52w > low_52w:
        pct = (price - low_52w) / (high_52w - low_52w)
        if pct > 0.80:
            score += 15
            reasons.append("Near 52-week high — strong momentum (+15)")
        elif pct > 0.60:
            score += 10
            reasons.append("Upper half of 52-week range (+10)")
        elif pct < 0.30:
            reasons.append("Near 52-week low — weak momentum (0)")

    short_pct = info.get("shortPercentOfFloat")
    if short_pct:
        if short_pct > 0.20:
            score -= 5
            reasons.append("High short interest — volatility risk (-5)")
        elif short_pct < 0.05:
            score += 5
            reasons.append("Low short interest (+5)")

    peg = info.get("pegRatio")
    if peg and peg > 0:
        if peg < 2:
            score += 10
            reasons.append("Reasonable PEG for growth rate (+10)")
        elif peg < 4:
            score += 5
            reasons.append("Acceptable PEG for high growth (+5)")

    margin = info.get("profitMargins")
    if margin:
        if margin > 0.10:
            score += 10
            reasons.append("Healthy margin despite growth focus (+10)")
        elif margin > 0:
            score += 5
            reasons.append("Profitable (+5)")

    rec_mean = info.get("recommendationMean")
    if rec_mean:
        if rec_mean < 2.0:
            score += 10
            reasons.append("Strong analyst buy consensus (+10)")
        elif rec_mean < 2.5:
            score += 5
            reasons.append("Positive analyst consensus (+5)")

    return max(0, min(100, score)), reasons

def get_growth_rating(score):
    if score >= 70:
        return "HIGH GROWTH"
    elif score >= 50:
        return "GROWTH"
    elif score >= 30:
        return "EMERGING"
    else:
        return "WEAK MOMENTUM"

def main():
    import yfinance as yf
    tickers = load_watchlist()
    print("Calculating growth scores for " + str(len(tickers)) + " tickers...")
    results = []
    for ticker in tickers:
        try:
            info = yf.Ticker(ticker).info
            score, reasons = score_growth(info)
            results.append({
                "ticker": ticker,
                "price": info.get("currentPrice"),
                "growth_score": score,
                "growth_rating": get_growth_rating(score),
                "growth_reasons": " | ".join(reasons),
            })
            print("  " + ticker + ": " + str(score) + "/100")
        except Exception as e:
            print("  " + ticker + " error: " + str(e))

    df = pd.DataFrame(results).sort_values("growth_score", ascending=False)
    df.to_csv("data/growth_scores.csv", index=False)
    print("Done! Saved to data/growth_scores.csv")

if __name__ == "__main__":
    main()
