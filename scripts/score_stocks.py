import pandas as pd
import json
import os

def score_stock(row):
    score = 0; reasons = []
    pe = row.get("pe_ratio")
    if pd.notna(pe) and pe > 0:
        if pe < 15:   score+=15; reasons.append("P/E under 15 (+15)")
        elif pe < 25: score+=10; reasons.append("P/E under 25 (+10)")
        elif pe < 35: score+=5;  reasons.append("P/E under 35 (+5)")
        else:         reasons.append(f"P/E high at {round(pe,1)} (0)")
    roe = row.get("roe")
    if pd.notna(roe):
        if roe > 0.30:   score+=15; reasons.append("ROE over 30% (+15)")
        elif roe > 0.15: score+=10; reasons.append("ROE over 15% (+10)")
        elif roe > 0:    score+=5;  reasons.append("ROE positive (+5)")
        else:            reasons.append("ROE negative (0)")
    fcf = row.get("free_cash_flow")
    if pd.notna(fcf):
        if fcf > 1_000_000_000: score+=15; reasons.append("FCF over $1B (+15)")
        elif fcf > 0:            score+=10; reasons.append("FCF positive (+10)")
        else:                    reasons.append("FCF negative (0)")
    de = row.get("debt_to_equity")
    if pd.notna(de):
        if de < 0.5:   score+=15; reasons.append("D/E under 0.5 (+15)")
        elif de < 1.0: score+=10; reasons.append("D/E under 1.0 (+10)")
        elif de < 2.0: score+=5;  reasons.append("D/E under 2.0 (+5)")
        else:          reasons.append(f"D/E high at {round(de,1)} (0)")
    margin = row.get("profit_margin")
    if pd.notna(margin):
        if margin > 0.20:   score+=15; reasons.append("Margin over 20% (+15)")
        elif margin > 0.10: score+=10; reasons.append("Margin over 10% (+10)")
        elif margin > 0:    score+=5;  reasons.append("Margin positive (+5)")
        else:               reasons.append("Margin negative (0)")
    growth = row.get("revenue_growth")
    if pd.notna(growth):
        if growth > 0.20:   score+=10; reasons.append("Revenue growth over 20% (+10)")
        elif growth > 0.10: score+=7;  reasons.append("Revenue growth over 10% (+7)")
        elif growth > 0:    score+=3;  reasons.append("Revenue growth positive (+3)")
        else:               reasons.append("Revenue shrinking (0)")
    return score, " | ".join(reasons)

def get_rating(score):
    if score >= 70:   return "STRONG BUY"
    elif score >= 50: return "BUY"
    elif score >= 30: return "WATCH"
    else:             return "AVOID"

def main():
    df = pd.read_csv("data/calculated_ratios.csv")
    results = []
    for _,row in df.iterrows():
        score, reasons = score_stock(row)
        results.append({"ticker":row["ticker"],"price":row["price"],
                         "score":score,"rating":get_rating(score),"reasons":reasons})
    out = pd.DataFrame(results).sort_values("score",ascending=False)
    out.to_csv("data/scores.csv",index=False)
    print(f"Done! Scored {len(results)} tickers")
    for _,row in out.iterrows():
        print(f"  {row['rating']:12} {row['ticker']:6} {row['score']}/85")

if __name__ == "__main__":
    main()
