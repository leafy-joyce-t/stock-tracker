import streamlit as st
import pandas as pd
import yfinance as yf
import json
import os
import requests
import threading
import subprocess
import sys
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

from dotenv import load_dotenv
import git

load_dotenv()

def auto_push(message="Update portfolio"):
    try:
        token = os.environ.get("GITHUB_TOKEN")
        repo  = git.Repo(".")
        repo.git.add("data/")
        repo.index.commit(message)
        origin = repo.remotes.origin
        url = origin.url
        if "https://" in url and "@" not in url:
            url = url.replace("https://", f"https://{token}@")
            origin.set_url(url)
        origin.push()
        return True
    except Exception as e:
        if "nothing to commit" in str(e).lower():
            return True
        print(f"Push error: {e}")
        return False

st.set_page_config(page_title="Stock Tracker", layout="wide")

PORTFOLIO_FILE  = "data/portfolio.json"
WATCHLIST_FILE  = "data/watchlist.json"
INDUSTRIES_FILE = "data/industries.json"
ANTHROPIC_API   = "https://api.anthropic.com/v1/messages"

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_current_price(ticker):
    try:
        stock = yf.Ticker(ticker)
        return round(stock.info.get("currentPrice") or stock.fast_info["last_price"], 2)
    except:
        return None

def get_price_on_date(ticker, date_str):
    try:
        hist = yf.Ticker(ticker).history(start=date_str, period="5d")
        return round(hist["Close"].iloc[0], 2) if not hist.empty else None
    except:
        return None

def get_period_start(period):
    today = datetime.today()
    return {"1W": today-timedelta(weeks=1), "1M": today-timedelta(days=30),
            "3M": today-timedelta(days=90), "6M": today-timedelta(days=180),
            "YTD": datetime(today.year,1,1), "1Y": today-timedelta(days=365),
            "All": None}.get(period)

def get_news(query, num=5):
    try:
        url = f"https://news.google.com/rss/search?q={query.replace(' ','+')}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
        soup = BeautifulSoup(r.content, "xml")
        items = soup.find_all("item")[:num]
        return [{"title": i.title.text, "link": i.link.text, "date": i.pubDate.text[:16]} for i in items]
    except:
        return []

def get_sector_from_yfinance(ticker):
    try:
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "")
        industry = info.get("industry", "")
        sector_color_map = {
            "Technology":           "#3498DB",
            "Financial Services":   "#2ECC71",
            "Healthcare":           "#1ABC9C",
            "Consumer Cyclical":    "#E67E22",
            "Consumer Defensive":   "#F39C12",
            "Communication Services":"#9B59B6",
            "Energy":               "#E74C3C",
            "Industrials":          "#34495E",
            "Basic Materials":      "#795548",
            "Real Estate":          "#00BCD4",
            "Utilities":            "#607D8B",
        }
        color = sector_color_map.get(sector, "#95A5A6")
        return sector or "Other", color, info.get("longBusinessSummary", "")
    except:
        return "Other", "#95A5A6", ""

def get_ai_summary(ticker, company_name, short_summary):
    try:
        prompt = f"""Give a 4-5 sentence investor-focused summary of {company_name} ({ticker}).
Cover: what the company does, its business model, main revenue streams, competitive position, and key risks.
Base it on this description: {short_summary[:500]}
Be concise and factual. No fluff."""
        r = requests.post(ANTHROPIC_API,
            headers={"Content-Type": "application/json"},
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 300,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=15)
        data = r.json()
        return data["content"][0]["text"]
    except:
        return "Could not generate AI summary."

def auto_fetch_ticker(ticker):
    def run():
        # Auto-classify industry
        industries = load_json(INDUSTRIES_FILE, {})
        if ticker not in industries:
            sector, color, _ = get_sector_from_yfinance(ticker)
            industries[ticker] = {"industry": sector, "color": color}
            save_json(INDUSTRIES_FILE, industries)
        # Run full pipeline so new ticker appears everywhere
        for script in [
            "scripts/fetch_financials.py",
            "scripts/calculate_ratios.py",
            "scripts/score_stocks.py",
            "scripts/compare_ratios.py",
        ]:
            subprocess.run([sys.executable, script], capture_output=True)
        # Push updated data to GitHub
        try:
            import git
            repo = git.Repo(".")
            repo.git.add("data/")
            repo.index.commit(f"Auto-add {ticker} data")
            repo.remotes.origin.push()
        except:
            pass
    threading.Thread(target=run, daemon=True).start()

st.title("📈 Stock Tracker Dashboard")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Portfolio", "Discover & Watchlist", "Ratio Analysis", "News", "Company Info"
])

# ─────────────────────────────────────────────────────────
# TAB 1: PORTFOLIO
# ─────────────────────────────────────────────────────────
with tab1:
    portfolio  = load_json(PORTFOLIO_FILE, [])
    industries = load_json(INDUSTRIES_FILE, {})

    col_h, col_r = st.columns([6,1])
    with col_h: st.subheader("Portfolio Performance")
    with col_r:
        if st.button("🔄 Refresh"): st.rerun()

    if not portfolio:
        st.info("No positions yet. Add one below.")
    else:
        period = st.radio("Period", ["1W","1M","3M","6M","YTD","1Y","All"],
                          horizontal=True, index=6)
        period_start = get_period_start(period)

        all_inds = list(set(industries.get(e["ticker"],{}).get("industry","Other") for e in portfolio))
        sel_inds = st.multiselect("Filter by industry", all_inds, default=all_inds)

        rows = []
        total_cost = total_value = total_period_cost = 0

        for i, entry in enumerate(portfolio):
            ticker   = entry["ticker"]
            ind_info = industries.get(ticker, {"industry":"Other","color":"#95A5A6"})
            if ind_info["industry"] not in sel_inds:
                continue
            shares    = entry["shares"]
            buy_price = entry["buy_price"]
            cost      = entry["cost"]
            now_price = get_current_price(ticker) or buy_price
            buy_date  = entry["buy_date"]

            if period_start and datetime.strptime(buy_date,"%Y-%m-%d") < period_start:
                period_buy = get_price_on_date(ticker, period_start.strftime("%Y-%m-%d")) or buy_price
            else:
                period_buy = buy_price

            period_cost = round(shares * period_buy, 2)
            value       = round(shares * now_price, 2)
            period_gain = round(value - period_cost, 2)
            period_pct  = round(period_gain/period_cost*100,2) if period_cost else 0
            total_gain  = round(value - cost, 2)
            total_pct   = round(total_gain/cost*100,2) if cost else 0

            total_cost        += cost
            total_value       += value
            total_period_cost += period_cost

            rows.append({"idx":i, "Ticker":ticker,
                "Industry": ind_info["industry"],
                "Shares":shares, "Buy Date":buy_date,
                "Buy $":f"${buy_price}", "Now $":f"${now_price}",
                f"{period} Gain": f"{'▲' if period_gain>=0 else '▼'} ${abs(period_gain)}",
                f"{period} %":   f"{'▲' if period_pct>=0 else '▼'} {abs(period_pct)}%",
                "All-Time":      f"{'▲' if total_gain>=0 else '▼'} ${abs(total_gain)} ({total_pct}%)",
                "Value":f"${value}"})

        tg = round(total_value-total_period_cost,2)
        tp = round(tg/total_period_cost*100,2) if total_period_cost else 0
        ag = round(total_value-total_cost,2)
        ap = round(ag/total_cost*100,2) if total_cost else 0

        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Invested",       f"${total_cost:,.2f}")
        c2.metric("Value",          f"${total_value:,.2f}")
        c3.metric(f"{period} Gain", f"${tg:,.2f}", f"{tp}%")
        c4.metric("All-Time Gain",  f"${ag:,.2f}", f"{ap}%")
        c5.metric("Positions",      len(rows))

        # Chart
        tickers    = list(set(e["ticker"] for e in portfolio))
        shares_map = {e["ticker"]:e["shares"] for e in portfolio}
        p_str = period_start.strftime("%Y-%m-%d") if period_start else min(e["buy_date"] for e in portfolio)
        chart_data = {}
        for t in tickers:
            h = yf.Ticker(t).history(start=p_str)
            if not h.empty:
                chart_data[t] = h["Close"] * shares_map.get(t,1)
        if chart_data:
            cdf = pd.DataFrame(chart_data).ffill()
            cdf["Total"] = cdf.sum(axis=1)
            st.line_chart(cdf["Total"])

        # By industry
        st.subheader("By industry")
        ind_groups = {}
        for row in rows:
            ind_groups.setdefault(row["Industry"],[]).append(row)
        for ind, ind_rows in ind_groups.items():
            color = industries.get(ind_rows[0]["Ticker"],{}).get("color","#ccc")
            st.markdown(f"<span style='background:{color};padding:2px 10px;border-radius:12px;color:white;font-size:13px'>{ind}</span>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(ind_rows).drop(columns=["idx","Industry"]), use_container_width=True)

        # Sell/Remove
        st.subheader("Sell or remove")
        opts = [f"{i}: {e['ticker']} ({e['shares']} shares, {e['buy_date']})" for i,e in enumerate(portfolio)]
        sel  = st.selectbox("Position", opts)
        si   = int(sel.split(":")[0])
        c1,c2 = st.columns(2)
        ss = c1.number_input("Shares to sell", min_value=0.01, max_value=float(portfolio[si]["shares"]), value=float(portfolio[si]["shares"]))
        sp = c2.number_input("Sell price (0=current)", min_value=0.0, value=0.0)
        cs,cr = st.columns(2)
        with cs:
            if st.button("💰 Sell"):
                e = portfolio[si]
                p = sp if sp>0 else get_current_price(e["ticker"])
                proceeds = round(ss*p,2); gain = round(proceeds-ss*e["buy_price"],2)
                if ss >= e["shares"]: portfolio.pop(si)
                else:
                    portfolio[si]["shares"] = round(e["shares"]-ss,4)
                    portfolio[si]["cost"]   = round(portfolio[si]["shares"]*e["buy_price"],2)
                save_json(PORTFOLIO_FILE, portfolio)
                auto_push("Sell position")
                st.success(f"Sold. Proceeds: ${proceeds} | Gain: ${gain}"); st.rerun()
        with cr:
            if st.button("🗑️ Remove"):
                portfolio.pop(si); save_json(PORTFOLIO_FILE, portfolio)
                auto_push("Remove position")
                st.success("Removed"); st.rerun()

    st.subheader("Add a position")
    c1,c2,c3,c4 = st.columns(4)
    nt = c1.text_input("Ticker", placeholder="AAPL").upper()
    ns = c2.number_input("Shares", min_value=0.01, value=1.0)
    nd = c3.date_input("Buy Date")
    np = c4.number_input("Buy Price (0=auto)", min_value=0.0, value=0.0)
    if st.button("➕ Add Position"):
        if nt:
            price = np if np>0 else (get_price_on_date(nt,str(nd)) or get_current_price(nt))
            portfolio.append({"ticker":nt,"shares":ns,"buy_date":str(nd),"buy_price":price,"cost":round(ns*price,2)})
            save_json(PORTFOLIO_FILE, portfolio)
            # Auto-add to watchlist and fetch
            wl = load_json(WATCHLIST_FILE, [])
            if nt not in wl:
                wl.append(nt); save_json(WATCHLIST_FILE, wl)
                auto_fetch_ticker(nt)
            st.success(f"Added {ns} shares of {nt} at ${price}!"); st.rerun()

# ─────────────────────────────────────────────────────────
# TAB 2: DISCOVER & WATCHLIST
# ─────────────────────────────────────────────────────────
with tab2:
    industries = load_json(INDUSTRIES_FILE, {})
    watchlist  = load_json(WATCHLIST_FILE, [])
    portfolio  = load_json(PORTFOLIO_FILE, [])
    owned      = set(e["ticker"] for e in portfolio)

    # Watchlist expander at top
    with st.expander(f"📋 Full watchlist ({len(watchlist)} stocks)"):
        if watchlist:
            cols = st.columns(4)
            for i, ticker in enumerate(watchlist):
                ind  = industries.get(ticker,{}).get("industry","Other")
                col  = industries.get(ticker,{}).get("color","#95A5A6")
                with cols[i%4]:
                    st.markdown(f"**{ticker}**<br><span style='background:{col};padding:1px 6px;border-radius:8px;color:white;font-size:11px'>{ind}</span>", unsafe_allow_html=True)
                    if st.button("✕", key=f"wl_rm_{ticker}"):
                        watchlist.remove(ticker); save_json(WATCHLIST_FILE, watchlist); st.rerun()
        st.markdown("---")
        st.markdown("**Add to watchlist**")
        wc1,wc2 = st.columns([3,1])
        new_wl_ticker = wc1.text_input("Ticker", placeholder="TSLA", key="wl_add").upper()
        if wc2.button("➕ Add", key="wl_add_btn"):
            if new_wl_ticker and new_wl_ticker not in watchlist:
                watchlist.append(new_wl_ticker)
                save_json(WATCHLIST_FILE, watchlist)
                auto_fetch_ticker(new_wl_ticker)
                st.success(f"Added {new_wl_ticker} — fetching data in background..."); st.rerun()

    st.subheader("🏆 Top stock picks")

    # Toggle
    show_mode = st.radio("Show", ["All tracked", "Not in portfolio"], horizontal=True)

    try:
        scores = pd.read_csv("data/scores.csv")
        ratios = pd.read_csv("data/calculated_ratios.csv")
        merged = scores.merge(ratios, on="ticker", how="left")
        merged["industry"] = merged["ticker"].map(lambda t: industries.get(t,{}).get("industry","Other"))
        merged["color"]    = merged["ticker"].map(lambda t: industries.get(t,{}).get("color","#95A5A6"))

        if show_mode == "Not in portfolio":
            merged = merged[~merged["ticker"].isin(owned)]

        top = merged[merged["rating"].isin(["STRONG BUY","BUY"])].sort_values("score", ascending=False).head(10)

        if top.empty:
            st.info("No strong buys found right now.")
        else:
            for _, row in top.iterrows():
                ticker  = row["ticker"]
                color   = "🟢" if row["rating"]=="STRONG BUY" else "🟡"
                ind_col = row["color"]
                in_port = "✓ Owned" if ticker in owned else ""

                with st.expander(f"{color} {ticker}  —  {row['rating']}  —  Score: {row['score']}/85  —  ${row.get('price_x', row.get('price',''))}  {in_port}"):
                    # Industry badge
                    st.markdown(f"<span style='background:{ind_col};padding:2px 10px;border-radius:12px;color:white;font-size:12px'>{row['industry']}</span>", unsafe_allow_html=True)
                    st.write("")

                    # Score reasons
                    st.markdown("**Why it scores well:**")
                    for reason in str(row.get("reasons","")).split(" | "):
                        st.write(f"• {reason}")

                    # Key ratios
                    st.markdown("**Key ratios:**")
                    rc1,rc2,rc3,rc4,rc5 = st.columns(5)
                    rc1.metric("P/E",          round(row["pe_ratio"],1)  if pd.notna(row.get("pe_ratio"))  else "N/A")
                    rc2.metric("ROE",          f"{round(row['roe']*100,1)}%" if pd.notna(row.get("roe")) else "N/A")
                    rc3.metric("Profit Margin",f"{round(row['profit_margin']*100,1)}%" if pd.notna(row.get("profit_margin")) else "N/A")
                    rc4.metric("D/E",          round(row["debt_to_equity"],2) if pd.notna(row.get("debt_to_equity")) else "N/A")
                    rc5.metric("Rev Growth",   f"{round(row['revenue_growth']*100,1)}%" if pd.notna(row.get("revenue_growth")) else "N/A")

                    # Add to portfolio button
                    if ticker not in owned:
                        if st.button(f"➕ Add {ticker} to portfolio", key=f"add_{ticker}"):
                            st.session_state[f"adding_{ticker}"] = True
                    if st.session_state.get(f"adding_{ticker}"):
                        ac1,ac2,ac3 = st.columns(3)
                        a_shares = ac1.number_input("Shares", min_value=0.01, value=1.0, key=f"sh_{ticker}")
                        a_date   = ac2.date_input("Buy Date", key=f"dt_{ticker}")
                        a_price  = ac3.number_input("Price (0=auto)", min_value=0.0, value=0.0, key=f"pr_{ticker}")
                        if st.button("Confirm", key=f"conf_{ticker}"):
                            price = a_price if a_price>0 else get_current_price(ticker)
                            port  = load_json(PORTFOLIO_FILE,[])
                            port.append({"ticker":ticker,"shares":a_shares,"buy_date":str(a_date),"buy_price":price,"cost":round(a_shares*price,2)})
                            save_json(PORTFOLIO_FILE, port)
                            st.success(f"Added {ticker}!"); st.rerun()
    except FileNotFoundError:
        st.warning("Run the scripts first to generate scores.")

# ─────────────────────────────────────────────────────────
# TAB 3: RATIO ANALYSIS
# ─────────────────────────────────────────────────────────
with tab3:
    st.subheader("Ratio Analysis")
    industries = load_json(INDUSTRIES_FILE, {})
    try:
        ratios = pd.read_csv("data/calculated_ratios.csv")
        ratios["Industry"] = ratios["ticker"].map(lambda t: industries.get(t,{}).get("industry","Other"))
        st.dataframe(ratios, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("P/E ratio")
            pe = ratios[ratios["pe_ratio"]>0].sort_values("pe_ratio")
            st.bar_chart(pe.set_index("ticker")["pe_ratio"])
        with col2:
            st.subheader("Return on equity")
            roe = ratios[ratios["roe"].notna()].sort_values("roe",ascending=False)
            st.bar_chart(roe.set_index("ticker")["roe"])

        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Profit margin")
            pm = ratios[ratios["profit_margin"].notna()].sort_values("profit_margin",ascending=False)
            st.bar_chart(pm.set_index("ticker")["profit_margin"])
        with col4:
            st.subheader("Revenue growth")
            rg = ratios[ratios["revenue_growth"].notna()].sort_values("revenue_growth",ascending=False)
            st.bar_chart(rg.set_index("ticker")["revenue_growth"])
    except FileNotFoundError:
        st.warning("Run calculate_ratios.py first")

# ─────────────────────────────────────────────────────────
# TAB 4: NEWS
# ─────────────────────────────────────────────────────────
with tab4:
    st.subheader("📰 Market News")
    st.markdown("### 🌍 General market")
    for item in get_news("stock market today", num=2):
        st.markdown(f"[{item['title']}]({item['link']}) — *{item['date']}*")
    st.markdown("---")

    industries = load_json(INDUSTRIES_FILE, {})
    watchlist  = load_json(WATCHLIST_FILE, [])
    portfolio  = load_json(PORTFOLIO_FILE, [])
    all_tickers = list(set([e["ticker"] for e in portfolio] + watchlist))

    ind_tickers = {}
    for ticker in all_tickers:
        ind = industries.get(ticker,{}).get("industry","Other")
        ind_tickers.setdefault(ind,[]).append(ticker)

    for industry, tickers in ind_tickers.items():
        color = industries.get(tickers[0],{}).get("color","#ccc")
        st.markdown(f"<span style='background:{color};padding:2px 10px;border-radius:12px;color:white;font-size:13px'>{industry} — {', '.join(tickers)}</span>", unsafe_allow_html=True)
        for item in get_news(f"{industry} stocks", num=5):
            st.markdown(f"[{item['title']}]({item['link']}) — *{item['date']}*")
        st.markdown("---")

# ─────────────────────────────────────────────────────────
# TAB 5: COMPANY INFO
# ─────────────────────────────────────────────────────────
with tab5:
    st.subheader("🏢 Company Profiles")
    industries = load_json(INDUSTRIES_FILE, {})
    watchlist  = load_json(WATCHLIST_FILE, [])

    selected_ticker = st.selectbox("Select a company", sorted(watchlist))
    if selected_ticker:
        info     = yf.Ticker(selected_ticker).info
        name     = info.get("longName", selected_ticker)
        short    = info.get("longBusinessSummary", "No description available.")
        sector   = info.get("sector","")
        industry = info.get("industry","")
        website  = info.get("website","")
        ind_info = industries.get(selected_ticker,{})

        col1, col2 = st.columns([3,1])
        with col1:
            st.markdown(f"## {name} ({selected_ticker})")
            if sector:
                color = ind_info.get("color","#95A5A6")
                st.markdown(f"<span style='background:{color};padding:2px 10px;border-radius:12px;color:white;font-size:13px'>{sector} — {industry}</span>", unsafe_allow_html=True)
            if website:
                st.markdown(f"[{website}]({website})")
        with col2:
            price = get_current_price(selected_ticker)
            if price: st.metric("Current Price", f"${price}")

        st.markdown("---")
        st.markdown("**Summary**")
        st.write(short[:400] + "..." if len(short)>400 else short)

        if st.button("🤖 Generate AI investor summary"):
            with st.spinner("Generating..."):
                ai = get_ai_summary(selected_ticker, name, short)
            st.markdown("**AI investor summary**")
            st.info(ai)

        # Key stats
        st.markdown("---")
        st.markdown("**Key stats**")
        sc1,sc2,sc3,sc4 = st.columns(4)
        sc1.metric("Market Cap",    f"${info.get('marketCap',0)/1e9:.1f}B" if info.get('marketCap') else "N/A")
        sc2.metric("Employees",     f"{info.get('fullTimeEmployees',0):,}" if info.get('fullTimeEmployees') else "N/A")
        sc3.metric("52W High",      f"${info.get('fiftyTwoWeekHigh','N/A')}")
        sc4.metric("52W Low",       f"${info.get('fiftyTwoWeekLow','N/A')}")
