# Stock Tracker

A full-stack investment research and portfolio tracking tool built from scratch — combining financial data pipelines, automated scoring, risk analysis, and a live dashboard.

Built as a demonstration of end-to-end product thinking: from identifying a problem, designing a solution, and shipping a working system with real data.

---

## What it does

- **Fetches raw financial statements** from Yahoo Finance and SEC EDGAR for any stock
- **Calculates key investment ratios** from scratch (P/E, ROE, FCF, D/E, profit margin, revenue growth) rather than trusting pre-calculated values
- **Scores each stock 0–85** based on fundamental health, then adjusts for risk signals including price momentum, short interest, insider ownership, analyst sentiment, and PEG ratio
- **Screens 100+ stocks automatically** every morning and surfaces the most undervalued ones not already in your portfolio
- **Tracks a hypothetical portfolio** with real-time P&L, time-period filters (1W, 1M, 3M, 6M, YTD, 1Y, All), and a portfolio value chart
- **Scrapes industry news** via Google News RSS, grouped by sector
- **Runs automatically** every weekday morning and evening via GitHub Actions — no manual intervention needed
- **Bilingual UI** — English and Chinese toggle built in

---

## Why I built it

Most retail investors rely on pre-calculated ratios from third-party sites without understanding what's in them or how reliable they are. This project was built to:

1. Understand the math behind investment metrics by calculating them from raw financial statements
2. Build a scoring system that goes beyond fundamentals to include real market signals (momentum, short interest, analyst sentiment)
3. Automate the daily research workflow so good opportunities surface automatically

---

## Technical stack

| Layer | Tools |
|---|---|
| Language | Python 3.13 |
| Data | yfinance, SEC EDGAR API, BeautifulSoup |
| Storage | SQLite / CSV, JSON |
| Dashboard | Streamlit |
| Automation | GitHub Actions (cron) |
| Version control | Git / GitHub |

---

## Project structure
---

## Scoring system

Each stock is scored out of 85 points across six fundamental dimensions:

| Signal | Max points |
|---|---|
| P/E Ratio | 15 |
| Return on Equity | 15 |
| Free Cash Flow | 15 |
| Debt to Equity | 15 |
| Profit Margin | 15 |
| Revenue Growth | 10 |

Scores are then adjusted by risk signals:

| Risk signal | Penalty |
|---|---|
| Down 15%+ in 3 months | -15 |
| High short interest (>20%) | -12 |
| More analyst downgrades than upgrades | -12 |
| Missed earnings 3+ of last 4 quarters | -12 |
| Revenue and earnings both shrinking | -15 |
| PEG ratio over 3 | -10 |
| Near 52-week high | -8 |

| Positive signal | Boost |
|---|---|
| PEG ratio under 1 | +10 |
| High insider ownership | +8 |
| Near 52-week low | +8 |
| Beat earnings all recent quarters | +8 |
| Strong analyst upgrades | +8 |

Final ratings: **Strong Buy** (70+), **Buy** (50–69), **Watch** (30–49), **Avoid** (<30)

---

## How to run locally

```bash
# Clone the repo
git clone https://github.com/leafy-joyce-t/stock-tracker.git
cd stock-tracker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the data pipeline
python scripts/fetch_financials.py
python scripts/risk_signals.py
python scripts/calculate_ratios.py
python scripts/score_stocks.py
python scripts/screener.py

# Launch the dashboard
streamlit run dashboard/app.py
```

Or just double-click **Stock Tracker.command** on the Desktop if set up locally.

---

## Automation

GitHub Actions runs the full pipeline twice daily on weekdays (9am and 7pm EST), commits updated CSVs back to the repo, and keeps all data fresh without any manual work.

---

## Key decisions & tradeoffs

**Why calculate ratios from scratch instead of using pre-built ones?**
Pre-calculated ratios from Yahoo Finance or Finviz can differ significantly from SEC filings. Building the calculation layer from raw statements makes the logic transparent and auditable.

**Why CSV/JSON instead of a database?**
For a personal tool running on a daily cron job with under 100 tickers, flat files are simpler to version control, inspect, and debug. The tradeoff is query speed at scale, which isn't a concern here.

**Why Streamlit instead of a full web framework?**
Streamlit lets you build a functional, interactive data UI in a fraction of the time of React or Django. For a solo portfolio project, shipping speed and maintainability matter more than customizability.

---

## What I learned

- How to read and interpret financial statements (income statement, balance sheet, cash flow)
- How investment ratios are calculated and what they actually measure
- How to build an end-to-end data pipeline from raw API data to a scored output
- How GitHub Actions works for scheduled automation
- How to think about signal quality — why momentum and risk signals matter as much as fundamentals

---

*Built by Eli — June 2026*
