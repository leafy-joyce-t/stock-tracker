import pandas as pd
import json
import os

WATCHLIST = ["RBLX", "HOOD", "META", "MSFT", "LMND", "NVDA", "SNDK", "MRNA", "NET", "AAPL"]

def load_data(ticker):
    base = f"data/financials/{ticker}"
    try:
        income   = pd.read_csv(f"{base}_income.csv",   index_col=0)
        balance  = pd.read_csv(f"{base}_balance.csv",  index_col=0)
        cashflow = pd.read_csv(f"{base}_cashflow.csv", index_col=0)
        with open(f"{base}_info.json") as f:
            info = json.load(f)
        return income, balance, cashflow, info
    except FileNotFoundError:
        print(f"  No data found for {ticker}")
        return None, None, None, None

def get_row(df, *names):
    for name in names:
        matches = [i for i in df.index if name.lower() in i.lower()]
        if matches:
            return df.loc[matches[0]]
    return None

def calculate_ratios(ticker):
    income, balance, cashflow, info = load_data(ticker)
    if income is None:
        return None
    price  = info.get("price")
    shares = info.get("shares")
    ratios = {"ticker": ticker, "price": price}
    col = income.columns[0]
    net_income = get_row(income, "Net Income")
    if net_income is not None and shares:
        eps = net_income[col] / shares
        ratios["eps"] = round(eps, 4)
        ratios["pe_ratio"] = round(price / eps, 2) if eps and eps > 0 else None
    equity = get_row(balance, "Stockholders Equity", "Total Equity", "Shareholders Equity")
    if net_income is not None and equity is not None:
        ratios["roe"] = round(net_income[col] / equity[col], 4) if equity[col] else None
    op_cf = get_row(cashflow, "Operating Cash Flow", "Total Cash From Operating")
    capex = get_row(cashflow, "Capital Expenditure", "Capital Expenditures")
    if op_cf is not None and capex is not None:
        ratios["free_cash_flow"] = op_cf[col] - abs(capex[col])
    total_debt = get_row(balance, "Total Debt", "Long Term Debt")
    if total_debt is not None and equity is not None:
        ratios["debt_to_equity"] = round(total_debt[col] / equity[col], 4) if equity[col] else None
    revenue = get_row(income, "Total Revenue", "Revenue")
    if net_income is not None and revenue is not None:
        ratios["profit_margin"] = round(net_income[col] / revenue[col], 4) if revenue[col] else None
    if revenue is not None and len(income.columns) >= 2:
        col_prev = income.columns[1]
        ratios["revenue_growth"] = round(
            (revenue[col] - revenue[col_prev]) / abs(revenue[col_prev]), 4
        ) if revenue[col_prev] else None
    return ratios

def main():
    os.makedirs("data", exist_ok=True)
    results = []
    for ticker in WATCHLIST:
        print(f"Calculating ratios for {ticker}...")
        ratios = calculate_ratios(ticker)
        if ratios:
            results.append(ratios)
            for k, v in ratios.items():
                if k not in ["ticker", "price"]:
                    print(f"  {k}: {v}")
    df = pd.DataFrame(results)
    df.to_csv("data/calculated_ratios.csv", index=False)
    print("\nDone! Saved to data/calculated_ratios.csv")
    print(df.to_string())

if __name__ == "__main__":
    main()
