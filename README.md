# Stock Tracker

A full-stack investment research and portfolio tracking tool built from scratch — combining financial data pipelines, dual scoring models, risk analysis, and a live dashboard.

Built as a demonstration of end-to-end product thinking: from identifying a problem, designing a solution, and shipping a working system with real data.

---

## What it does

- **Fetches raw financial statements** from Yahoo Finance and SEC EDGAR for any stock
- **Calculates key investment ratios** from scratch (P/E, ROE, FCF, D/E, profit margin, revenue growth) rather than trusting pre-calculated values
- **Scores each stock two ways**:
  - **Value/Stability mode** (0–85): rewards low P/E, high ROE, strong FCF, low debt
  - **Growth/Momentum mode** (0–100): rewards revenue acceleration, earnings growth, momentum, and analyst sentiment — built specifically because the value model was underrating legitimate high-growth winners like HOOD and LMND
- **Adjusts every score with real risk signals**: price momentum, short interest, insider ownership, analyst upgrades/downgrades, earnings surprise history, and PEG ratio
- **Screens 100+ stocks automatically** every morning and surfaces the most undervalued ones not already in your portfolio, using the same risk-adjusted scoring as the rest of the app
- **Tracks a real portfolio** with live current prices, time-period filters (1W, 1M, 3M, 6M, YTD, 1Y, All), buy/sell/remove actions, and a portfolio value chart
- **Live company profiles** — sector, industry, 52-week range, market cap, employee count, and full business description for any tracked ticker
- **Industry-grouped news** scraped from Google News RSS, plus general market headlines at the top
- **Color-coded ratio table** with search by ticker and filter by industry — green/orange/red highlighting based on standard investing thresholds
- **Auto-classifies new tickers** by sector the moment you add them to the watchlist, then runs the full pipeline in the background
- **Runs automatically** every weekday morning and evening via GitHub Actions — fetches, scores, and commits fresh data with zero manual intervention
- **Bilingual UI** — English/Chinese toggle
- **One-click desktop launcher** — a `.command` file that pulls latest data and opens the dashboard with no terminal needed

---

## Why I built it

Most retail investors rely on pre-calculated ratios from third-party sites without understanding what's in them or how reliable they are. This project was built to:

1. Understand the math behind investment metrics by calculating them from raw financial statements
2. Build a scoring system that goes beyond fundamentals to include real market signals (momentum, short interest, analyst sentiment)
3. Recognize that "good fundamentals" and "good investment right now" are different questions — which led to building a second, growth-oriented scoring lens
4. Automate the daily research workflow so good opportunities surface automatically, without me having to manually compare dozens of tickers

---

## Technical stack

| Layer | Tools |
|---|---|
| Language | Python 3.13 |
| Data | yfinance, SEC EDGAR API, BeautifulSoup |
| Storage | CSV, JSON |
| Dashboard | Streamlit |
| Automation | GitHub Actions (cron, twice daily) |
| Version control | Git / GitHub |

---

## Project structure
