import streamlit as st
import pandas as pd
import yfinance as yf
import json, os, requests, threading, subprocess, sys
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Stock Tracker", layout="wide")

PORTFOLIO_FILE  = "data/portfolio.json"
WATCHLIST_FILE  = "data/watchlist.json"
INDUSTRIES_FILE = "data/industries.json"

# ── Helpers ──────────────────────────────────────────────
def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f: return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=2)

def all_tickers():
    wl   = load_json(WATCHLIST_FILE, [])
    port = load_json(PORTFOLIO_FILE, [])
    return list(set(wl + [e["ticker"] for e in port]))

def get_current_price(ticker):
    try:
        s = yf.Ticker(ticker)
        return round(s.info.get("currentPrice") or s.fast_info["last_price"], 2)
    except: return None

def get_price_on_date(ticker, date_str):
    try:
        h = yf.Ticker(ticker).history(start=date_str, period="5d")
        return round(h["Close"].iloc[0], 2) if not h.empty else None
    except: return None

def get_period_start(period):
    t = datetime.today()
    return {"1W":t-timedelta(weeks=1),"1M":t-timedelta(days=30),
            "3M":t-timedelta(days=90),"6M":t-timedelta(days=180),
            "YTD":datetime(t.year,1,1),"1Y":t-timedelta(days=365),"All":None}.get(period)

def get_news(query, num=5):
    try:
        url = f"https://news.google.com/rss/search?q={query.replace(' ','+')}&hl=en-US&gl=US&ceid=US:en"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
        soup = BeautifulSoup(r.content, "xml")
        return [{"title":i.title.text,"link":i.link.text,"date":i.pubDate.text[:16]}
                for i in soup.find_all("item")[:num]]
    except: return []

def get_sector(ticker):
    try:
        info = yf.Ticker(ticker).info
        sector_colors = {
            "Technology":"#3498DB","Financial Services":"#2ECC71",
            "Healthcare":"#1ABC9C","Consumer Cyclical":"#E67E22",
            "Consumer Defensive":"#F39C12","Communication Services":"#9B59B6",
            "Energy":"#E74C3C","Industrials":"#34495E",
            "Basic Materials":"#795548","Real Estate":"#00BCD4","Utilities":"#607D8B"
        }
        sector = info.get("sector","Other")
        return sector, sector_colors.get(sector,"#95A5A6")
    except: return "Other","#95A5A6"

def auto_push(message="Update data"):
    try:
        import git
        token = os.environ.get("GITHUB_TOKEN","")
        repo  = git.Repo(".")
        repo.git.add("data/")
        repo.index.commit(message)
        origin = repo.remotes.origin
        url = origin.url
        if "https://" in url and "@" not in url:
            url = url.replace("https://", f"https://{token}@")
            origin.set_url(url)
        origin.push()
    except: pass

def auto_fetch(ticker):
    def run():
        industries = load_json(INDUSTRIES_FILE, {})
        if ticker not in industries:
            sector, color = get_sector(ticker)
            industries[ticker] = {"industry": sector, "color": color}
            save_json(INDUSTRIES_FILE, industries)
        for script in ["scripts/fetch_financials.py","scripts/calculate_ratios.py",
                       "scripts/score_stocks.py","scripts/compare_ratios.py"]:
            subprocess.run([sys.executable, script], capture_output=True)
        auto_push(f"Add {ticker}")
    threading.Thread(target=run, daemon=True).start()

# ── UI ───────────────────────────────────────────────────
st.title("📈 Stock Tracker Dashboard")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Portfolio", "Stock Scores", "Discover & Watchlist", "Ratio Analysis", "News & Company Info"
])

# ════════════════════════════════════════════════════════
# TAB 1 — PORTFOLIO
# ════════════════════════════════════════════════════════
with tab1:
    portfolio  = load_json(PORTFOLIO_FILE, [])
    industries = load_json(INDUSTRIES_FILE, {})

    ch, cr = st.columns([6,1])
    ch.subheader("Portfolio Performance")
    if cr.button("🔄 Refresh"): st.rerun()

    if portfolio:
        period = st.radio("Period",["1W","1M","3M","6M","YTD","1Y","All"],horizontal=True,index=6)
        ps     = get_period_start(period)
        all_inds = list(set(industries.get(e["ticker"],{}).get("industry","Other") for e in portfolio))
        sel_inds = st.multiselect("Filter by industry", all_inds, default=all_inds)

        rows=[]; tc=tv=tpc=0
        for i,entry in enumerate(portfolio):
            t   = entry["ticker"]
            ind = industries.get(t,{})
            if ind.get("industry","Other") not in sel_inds: continue
            sh  = entry["shares"]; bp=entry["buy_price"]; cost=entry["cost"]
            now = get_current_price(t) or bp
            bd  = entry["buy_date"]
            pbp = get_price_on_date(t,ps.strftime("%Y-%m-%d")) or bp if ps and datetime.strptime(bd,"%Y-%m-%d")<ps else bp
            pc  = round(sh*pbp,2); val=round(sh*now,2)
            pg  = round(val-pc,2); pp=round(pg/pc*100,2) if pc else 0
            ag  = round(val-cost,2); ap=round(ag/cost*100,2) if cost else 0
            tc+=cost; tv+=val; tpc+=pc
            rows.append({"idx":i,"Ticker":t,
                "Industry":ind.get("industry","Other"),
                "Shares":sh,"Buy Date":bd,"Buy $":f"${bp}","Now $":f"${now}",
                f"{period} Gain":f"{'▲' if pg>=0 else '▼'} ${abs(pg)}",
                f"{period} %":f"{'▲' if pp>=0 else '▼'} {abs(pp)}%",
                "All-Time":f"{'▲' if ag>=0 else '▼'} ${abs(ag)} ({ap}%)","Value":f"${val}"})

        tpg=round(tv-tpc,2); tpp=round(tpg/tpc*100,2) if tpc else 0
        tag=round(tv-tc,2);  tap=round(tag/tc*100,2)  if tc  else 0
        c1,c2,c3,c4,c5=st.columns(5)
        c1.metric("Invested",f"${tc:,.2f}"); c2.metric("Value",f"${tv:,.2f}")
        c3.metric(f"{period} Gain",f"${tpg:,.2f}",f"{tpp}%")
        c4.metric("All-Time Gain",f"${tag:,.2f}",f"{tap}%")
        c5.metric("Positions",len(rows))

        # Chart
        tickers_p  = list(set(e["ticker"] for e in portfolio))
        shares_map = {e["ticker"]:e["shares"] for e in portfolio}
        p_str = ps.strftime("%Y-%m-%d") if ps else min(e["buy_date"] for e in portfolio)
        cdata = {}
        for t in tickers_p:
            h = yf.Ticker(t).history(start=p_str)
            if not h.empty: cdata[t]=h["Close"]*shares_map.get(t,1)
        if cdata:
            cdf=pd.DataFrame(cdata).ffill(); cdf["Total"]=cdf.sum(axis=1)
            st.line_chart(cdf["Total"])

        # By industry
        st.subheader("By industry")
        ind_groups={}
        for row in rows: ind_groups.setdefault(row["Industry"],[]).append(row)
        for ind,ind_rows in ind_groups.items():
            col=industries.get(ind_rows[0]["Ticker"],{}).get("color","#ccc")
            st.markdown(f"<span style='background:{col};padding:2px 10px;border-radius:12px;color:white;font-size:13px'>{ind}</span>",unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(ind_rows).drop(columns=["idx","Industry"]),use_container_width=True)

        # Sell/Remove
        st.subheader("Sell or remove")
        opts=[f"{i}: {e['ticker']} ({e['shares']} shares, {e['buy_date']})" for i,e in enumerate(portfolio)]
        sel=st.selectbox("Position",opts); si=int(sel.split(":")[0])
        c1,c2=st.columns(2)
        ss=c1.number_input("Shares to sell",min_value=0.01,max_value=float(portfolio[si]["shares"]),value=float(portfolio[si]["shares"]))
        sp=c2.number_input("Sell price (0=current)",min_value=0.0,value=0.0)
        cs,cr2=st.columns(2)
        with cs:
            if st.button("💰 Sell"):
                e=portfolio[si]; p=sp if sp>0 else get_current_price(e["ticker"])
                proceeds=round(ss*p,2); gain=round(proceeds-ss*e["buy_price"],2)
                if ss>=e["shares"]: portfolio.pop(si)
                else:
                    portfolio[si]["shares"]=round(e["shares"]-ss,4)
                    portfolio[si]["cost"]=round(portfolio[si]["shares"]*e["buy_price"],2)
                save_json(PORTFOLIO_FILE,portfolio); auto_push("Sell position")
                st.success(f"Sold. Proceeds: ${proceeds} | Gain: ${gain}"); st.rerun()
        with cr2:
            if st.button("🗑️ Remove"):
                portfolio.pop(si); save_json(PORTFOLIO_FILE,portfolio); auto_push("Remove position")
                st.success("Removed"); st.rerun()

    st.subheader("Add a position")
    c1,c2,c3,c4=st.columns(4)
    nt=c1.text_input("Ticker",placeholder="AAPL").upper()
    ns=c2.number_input("Shares",min_value=0.01,value=1.0)
    nd=c3.date_input("Buy Date")
    np_=c4.number_input("Buy Price (0=auto)",min_value=0.0,value=0.0)
    if st.button("➕ Add Position"):
        if nt:
            price=np_ if np_>0 else (get_price_on_date(nt,str(nd)) or get_current_price(nt))
            portfolio.append({"ticker":nt,"shares":ns,"buy_date":str(nd),"buy_price":price,"cost":round(ns*price,2)})
            save_json(PORTFOLIO_FILE,portfolio)
            wl=load_json(WATCHLIST_FILE,[])
            if nt not in wl: wl.append(nt); save_json(WATCHLIST_FILE,wl); auto_fetch(nt)
            auto_push(f"Add {nt} to portfolio")
            st.success(f"Added {ns} shares of {nt} at ${price}! Fetching data in background..."); st.rerun()

# ════════════════════════════════════════════════════════
# TAB 2 — STOCK SCORES
# ════════════════════════════════════════════════════════
with tab2:
    st.subheader("📊 Stock Scores & Ratings")
    industries = load_json(INDUSTRIES_FILE, {})
    try:
        scores = pd.read_csv("data/scores.csv")
        for _,row in scores.iterrows():
            t    = row["ticker"]
            ind  = industries.get(t,{})
            col  = ind.get("color","#95A5A6")
            icon = "🟢" if row["rating"] in ["STRONG BUY","BUY"] else "🟡" if row["rating"]=="WATCH" else "🔴"
            with st.expander(f"{icon} {t}  —  {row['rating']}  —  Score: {row['score']}/85  —  ${row['price']}"):
                st.markdown(f"<span style='background:{col};padding:2px 10px;border-radius:12px;color:white;font-size:12px'>{ind.get('industry','Other')}</span>",unsafe_allow_html=True)
                st.write("")
                for reason in str(row.get("reasons","")).split(" | "):
                    st.write(f"• {reason}")
    except FileNotFoundError:
        st.warning("Run score_stocks.py first")

# ════════════════════════════════════════════════════════
# TAB 3 — DISCOVER & WATCHLIST
# ════════════════════════════════════════════════════════
with tab3:
    industries = load_json(INDUSTRIES_FILE, {})
    watchlist  = load_json(WATCHLIST_FILE, [])
    portfolio  = load_json(PORTFOLIO_FILE, [])
    owned      = set(e["ticker"] for e in portfolio)

    with st.expander(f"📋 Full watchlist ({len(watchlist)} stocks)"):
        if watchlist:
            cols=st.columns(4)
            for i,t in enumerate(watchlist):
                ind=industries.get(t,{})
                with cols[i%4]:
                    st.markdown(f"**{t}**<br><span style='background:{ind.get('color','#95A5A6')};padding:1px 6px;border-radius:8px;color:white;font-size:11px'>{ind.get('industry','Other')}</span>",unsafe_allow_html=True)
                    if st.button("✕",key=f"wl_rm_{t}"):
                        watchlist.remove(t); save_json(WATCHLIST_FILE,watchlist); st.rerun()
        wc1,wc2=st.columns([3,1])
        nwt=wc1.text_input("Add ticker",placeholder="TSLA",key="wl_add").upper()
        if wc2.button("➕ Add",key="wl_btn"):
            if nwt and nwt not in watchlist:
                watchlist.append(nwt); save_json(WATCHLIST_FILE,watchlist)
                auto_fetch(nwt)
                st.success(f"Added {nwt} — fetching data in background..."); st.rerun()

    st.subheader("🏆 Top stock picks")
    mode=st.radio("Show",["All tracked","Not in portfolio"],horizontal=True)
    try:
        scores=pd.read_csv("data/scores.csv")
        ratios=pd.read_csv("data/calculated_ratios.csv")
        merged=scores.merge(ratios,on="ticker",how="left")
        merged["industry"]=merged["ticker"].map(lambda t:industries.get(t,{}).get("industry","Other"))
        merged["color"]   =merged["ticker"].map(lambda t:industries.get(t,{}).get("color","#95A5A6"))
        if mode=="Not in portfolio": merged=merged[~merged["ticker"].isin(owned)]
        top=merged[merged["rating"].isin(["STRONG BUY","BUY"])].sort_values("score",ascending=False).head(10)
        if top.empty: st.info("No strong buys right now.")
        else:
            for _,row in top.iterrows():
                t=row["ticker"]; icon="🟢" if row["rating"]=="STRONG BUY" else "🟡"
                owned_tag="✓ Owned" if t in owned else ""
                price_val = row.get("price_x", row.get("price",""))
                with st.expander(f"{icon} {t}  —  {row['rating']}  —  Score: {row['score']}/85  —  ${price_val}  {owned_tag}"):
                    st.markdown(f"<span style='background:{row['color']};padding:2px 10px;border-radius:12px;color:white;font-size:12px'>{row['industry']}</span>",unsafe_allow_html=True)
                    st.write("")
                    for reason in str(row.get("reasons","")).split(" | "): st.write(f"• {reason}")
                    rc1,rc2,rc3,rc4,rc5=st.columns(5)
                    rc1.metric("P/E",          round(row["pe_ratio"],1)           if pd.notna(row.get("pe_ratio"))       else "N/A")
                    rc2.metric("ROE",          f"{round(row['roe']*100,1)}%"      if pd.notna(row.get("roe"))            else "N/A")
                    rc3.metric("Profit Margin",f"{round(row['profit_margin']*100,1)}%" if pd.notna(row.get("profit_margin")) else "N/A")
                    rc4.metric("D/E",          round(row["debt_to_equity"],2)     if pd.notna(row.get("debt_to_equity")) else "N/A")
                    rc5.metric("Rev Growth",   f"{round(row['revenue_growth']*100,1)}%" if pd.notna(row.get("revenue_growth")) else "N/A")
                    if t not in owned:
                        if st.button(f"➕ Add {t} to portfolio",key=f"add_{t}"):
                            st.session_state[f"adding_{t}"]=True
                    if st.session_state.get(f"adding_{t}"):
                        ac1,ac2,ac3=st.columns(3)
                        a_sh=ac1.number_input("Shares",min_value=0.01,value=1.0,key=f"sh_{t}")
                        a_dt=ac2.date_input("Buy Date",key=f"dt_{t}")
                        a_pr=ac3.number_input("Price (0=auto)",min_value=0.0,value=0.0,key=f"pr_{t}")
                        if st.button("Confirm",key=f"conf_{t}"):
                            price=a_pr if a_pr>0 else get_current_price(t)
                            port=load_json(PORTFOLIO_FILE,[])
                            port.append({"ticker":t,"shares":a_sh,"buy_date":str(a_dt),"buy_price":price,"cost":round(a_sh*price,2)})
                            save_json(PORTFOLIO_FILE,port); auto_push(f"Add {t}")
                            st.success(f"Added {t}!"); st.rerun()
    except FileNotFoundError:
        st.warning("Run the scripts first to generate scores.")

# ════════════════════════════════════════════════════════
# TAB 4 — RATIO ANALYSIS
# ════════════════════════════════════════════════════════
with tab4:
    st.subheader("📐 Ratio Analysis")
    industries=load_json(INDUSTRIES_FILE,{})
    try:
        ratios=pd.read_csv("data/calculated_ratios.csv")
        ratios["Industry"]=ratios["ticker"].map(lambda t:industries.get(t,{}).get("industry","Other"))
        st.dataframe(ratios,use_container_width=True)
        c1,c2=st.columns(2)
        with c1:
            st.subheader("P/E Ratio"); pe=ratios[ratios["pe_ratio"]>0].sort_values("pe_ratio")
            st.bar_chart(pe.set_index("ticker")["pe_ratio"])
        with c2:
            st.subheader("Return on Equity"); roe=ratios[ratios["roe"].notna()].sort_values("roe",ascending=False)
            st.bar_chart(roe.set_index("ticker")["roe"])
        c3,c4=st.columns(2)
        with c3:
            st.subheader("Profit Margin"); pm=ratios[ratios["profit_margin"].notna()].sort_values("profit_margin",ascending=False)
            st.bar_chart(pm.set_index("ticker")["profit_margin"])
        with c4:
            st.subheader("Revenue Growth"); rg=ratios[ratios["revenue_growth"].notna()].sort_values("revenue_growth",ascending=False)
            st.bar_chart(rg.set_index("ticker")["revenue_growth"])
    except FileNotFoundError:
        st.warning("Run calculate_ratios.py first")

# ════════════════════════════════════════════════════════
# TAB 5 — NEWS & COMPANY INFO
# ════════════════════════════════════════════════════════
with tab5:
    news_tab, company_tab = st.tabs(["📰 News", "🏢 Company Info"])

    with news_tab:
        st.markdown("### 🌍 General market")
        for item in get_news("stock market today",num=2):
            st.markdown(f"[{item['title']}]({item['link']}) — *{item['date']}*")
        st.markdown("---")
        industries=load_json(INDUSTRIES_FILE,{})
        tickers_all=all_tickers()
        ind_map={}
        for t in tickers_all:
            ind=industries.get(t,{}).get("industry","Other")
            ind_map.setdefault(ind,[]).append(t)
        for ind,tickers_in_ind in ind_map.items():
            col=industries.get(tickers_in_ind[0],{}).get("color","#ccc")
            st.markdown(f"<span style='background:{col};padding:2px 10px;border-radius:12px;color:white;font-size:13px'>{ind} — {', '.join(tickers_in_ind)}</span>",unsafe_allow_html=True)
            for item in get_news(f"{ind} stocks news",num=5):
                st.markdown(f"[{item['title']}]({item['link']}) — *{item['date']}*")
            st.markdown("---")

    with company_tab:
        st.subheader("Company Profiles")
        tickers_all=sorted(all_tickers())
        industries=load_json(INDUSTRIES_FILE,{})
        sel=st.selectbox("Select a company",tickers_all)
        if sel:
            info=yf.Ticker(sel).info
            name=info.get("longName",sel)
            short=info.get("longBusinessSummary","No description available.")
            sector=info.get("sector","")
            industry_label=info.get("industry","")
            website=info.get("website","")
            ind_info=industries.get(sel,{})
            col_=ind_info.get("color","#95A5A6")
            c1,c2=st.columns([3,1])
            with c1:
                st.markdown(f"## {name} ({sel})")
                if sector:
                    st.markdown(f"<span style='background:{col_};padding:2px 10px;border-radius:12px;color:white;font-size:13px'>{sector} — {industry_label}</span>",unsafe_allow_html=True)
                if website: st.markdown(f"[{website}]({website})")
            with c2:
                p=get_current_price(sel)
                if p: st.metric("Current Price",f"${p}")
            st.markdown("---")
            st.markdown("**About**")
            st.write(short)
            st.markdown("---")
            st.markdown("**Key stats**")
            s1,s2,s3,s4=st.columns(4)
            s1.metric("Market Cap",f"${info.get('marketCap',0)/1e9:.1f}B" if info.get('marketCap') else "N/A")
            s2.metric("Employees",f"{info.get('fullTimeEmployees',0):,}" if info.get('fullTimeEmployees') else "N/A")
            s3.metric("52W High",f"${info.get('fiftyTwoWeekHigh','N/A')}")
            s4.metric("52W Low",f"${info.get('fiftyTwoWeekLow','N/A')}")
