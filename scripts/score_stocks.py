import pandas as pd
import json
import os
import ast

def load_watchlist():
    wl   = json.load(open("data/watchlist.json")) if os.path.exists("data/watchlist.json") else []
    port = json.load(open("data/portfolio.json"))  if os.path.exists("data/portfolio.json")  else []
    return list(set(wl + [e["ticker"] for e in port]))

def score_stock(row):
    score = 0
    reasons = []

    pe = row.get("pe_ratio")
    if pd.notna(pe) and pe > 0:
        if pe < 15:   score += 15; reasons.append("P/E under 15 (+15)")
        elif pe < 25: score += 10; reasons.append("P/E under 25 (+10)")
        elif pe < 35: score += 5;  reasons.append("P/E under 35 (+5)")
        else:         reasons.append(f"P/E high at {round(pe,1)} (0)")

    roe = row.get("roe")
    if pd.notna(roe):
        if roe > 0.30:   score += 15; reasons.append("ROE over 30% (+15)")
        elif roe > 0.15: score += 10; reasons.append("ROE over 15% (+10)")
        elif roe > 0:    score += 5;  reasons.append("ROE positive (+5)")
        else:            reasons.append("ROE negative (0)")

    fcf = row.get("free_cash_flow")
    if pd.notna(fcf):
        if fcf > 1_000_000_000: score += 15; reasons.append("FCF over $1B (+15)")
        elif fcf > 0:            score += 10; reasons.append("FCF positive (+10)")
        else:                    reasons.append("FCF negative (0)")

    de = row.get("debt_to_equity")
    if pd.notna(de):
        if de < 0.5:   score += 15; reasons.append("D/E under 0.5 (+15)")
        elif de < 1.0: score += 10; reasons.append("D/E under 1.0 (+10)")
        elif de < 2.0: score += 5;  reasons.append("D/E under 2.0 (+5)")
        else:          reasons.append(f"D/E high at {round(de,1)} (0)")

    margin = row.get("profit_margin")
    if pd.notna(margin):
        if margin > 0.20:   score += 15; reasons.append("Margin over 20% (+15)")
        elif margin > 0.10: score += 10; reasons.append("Margin over 10% (+10)")
        elif margin > 0:    score += 5;  reasons.append("Margin positive (+5)")
        else:               reasons.append("Margin negative (0)")

    growth = row.get("revenue_growth")
    if pd.notna(growth):
        if growth > 0.20:   score += 10; reasons.append("Revenue growth over 20% (+10)")
        elif growth > 0.10: score += 7;  reasons.append("Revenue growth over 10% (+7)")
        elif growth > 0:    score += 3;  reasons.append("Revenue growth positive (+3)")
        else:               reasons.append("Revenue shrinking (0)")

    return score, " | ".join(reasons)

def get_rating(score):
    if score >= 70:   return "STRONG BUY"
    elif score >= 50: return "BUY"
    elif score >= 30: return "WATCH"
    else:             return "AVOID"

def main():
    df = pd.read_csv("data/calculated_ratios.csv")

    # Load risk signals if available
    risk_df = None
    if os.path.exists("data/risk_signals.csv"):
        risk_df = pd.read_csv("data/risk_signals.csv")

    results = []
    for _, row in df.iterrows():
        ticker = row["ticker"]
        score, reasons = score_stock(row)

        risk_flags  = []
        bonus_flags = []

        # Apply risk signals
        if risk_df is not None:
            risk_row = risk_df[risk_df["ticker"] == ticker]
            if not risk_row.empty:
                r = risk_row.iloc[0]
                penalty = r.get("penalty", 0)
                boost   = r.get("boost", 0)
                score   = max(0, score - penalty + boost)

                try:
                    risk_flags  = ast.literal_eval(r.get("risk_flags",  "[]")) if isinstance(r.get("risk_flags"),  str) else []
                    bonus_flags = ast.literal_eval(r.get("bonus_flags", "[]")) if isinstance(r.get("bonus_flags"), str) else []
                except:
                    pass

        all_reasons = reasons.split(" | ") + bonus_flags + ["⚠️ " + f for f in risk_flags]

        results.append({
            "ticker":   ticker,
            "price":    row["price"],
            "score":    score,
            "rating":   get_rating(score),
            "reasons":  " | ".join(all_reasons),
        })

    out = pd.DataFrame(results).sort_values("score", ascending=False)
    out.to_csv("data/scores.csv", index=False)
    print(f"Done! Scored {len(results)} tickers")
    for _, row in out.iterrows():
        print(f"  {row['rating']:12} {row['ticker']:6} {row['score']}/85+")

if __name__ == "__main__":
    main()

