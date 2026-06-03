
import streamlit as st
import pandas as pd
import yfinance as yf
import json, os, requests, subprocess, sys
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Stock Tracker", layout="wide")

PORTFOLIO_FILE  = "data/portfolio.json"
WATCHLIST_FILE  = "data/watchlist.json"
INDUSTRIES_FILE = "data/industries.json"

def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def all_tickers():
    wl   = load_json(WATCHLIST_FILE, [])
    port = load_json(PORTFOLIO_FILE, [])
    return list(set(wl + [e["ticker"] for e in port]))

def get_current_price(ticker):
    try:
        s = yf.Ticker(ticker)
        p = s.info.get("currentPrice")
        if p:
            return round(float(p), 2)
        h = s.history(period="1d")
        if not h.empty:
            return round(float(h["Close"].iloc[-1]), 2)
        return None
    except:
        return None
def get_period_start(period):
    t = datetime.today()
    mapping = {
        "1W":  t - timedelta(weeks=1),
        "1M":  t - timedelta(days=30),
        "3M":  t - timedelta(days=90),
        "6M":  t - timedelta(days=180),
        "YTD": datetime(t.year, 1, 1),
        "1Y":  t - timedelta(days=365),
        "All": None
    }
    return mapping.get(period)

def get_news(query, num=5):
    try:
        q   = query.replace(" ", "+")
        url = "https://news.google.com/rss/search?q=" + q + "&hl=en-US&gl=US&ceid=US:en"
        r   = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        soup = BeautifulSoup(r.content, "xml")
        items = soup.find_all("item")[:num]
        return [{"title": i.title.text, "link": i.link.text, "date": i.pubDate.text[:16]} for i in items]
    except:
        return []

def get_sector(ticker):
    try:
        info = yf.Ticker(ticker).info
        sector = info.get("sector", "Other")
        colors = {
            "Technology": "#3498DB",
            "Financial Services": "#2ECC71",
            "Healthcare": "#1ABC9C",
            "Consumer Cyclical": "#E67E22",
            "Consumer Defensive": "#F39C12",
            "Communication Services": "#9B59B6",
            "Energy": "#E74C3C",
            "Industrials": "#34495E",
            "Basic Materials": "#795548",
            "Real Estate": "#00BCD4",
            "Utilities": "#607D8B"
        }
        return sector, colors.get(sector, "#95A5A6")
    except:
        return "Other", "#95A5A6"

def auto_push(message):
    try:
        import git
        token = os.environ.get("GITHUB_TOKEN", "")
        repo  = git.Repo(".")
        repo.git.add("data/")
        repo.index.commit(message)
        origin = repo.remotes.origin
        url = origin.url
        if "https://" in url and "@" not in url:
            url = url.replace("https://", "https://" + token + "@")
            origin.set_url(url)
        origin.push()
    except:
        pass

def run_pipeline():
    scripts = [
        "scripts/fetch_financials.py",
        "scripts/calculate_ratios.py",
        "scripts/score_stocks.py",
    ]
    for script in scripts:
        subprocess.run([sys.executable, script])

def add_to_watchlist(ticker):
    industries = load_json(INDUSTRIES_FILE, {})
    if ticker not in industries:
        sector, color = get_sector(ticker)
        industries[ticker] = {"industry": sector, "color": color}
        save_json(INDUSTRIES_FILE, industries)
    wl = load_json(WATCHLIST_FILE, [])
    if ticker not in wl:
        wl.append(ticker)
        save_json(WATCHLIST_FILE, wl)
    run_pipeline()
    auto_push("Add " + ticker)

def ind_badge(ticker, industries):
    ind   = industries.get(ticker, {})
    color = ind.get("color", "#95A5A6")
    label = ind.get("industry", "Other")
    return "<span style=\'background:" + color + ";padding:2px 10px;border-radius:12px;color:white;font-size:12px\'>" + label + "</span>"

# Language toggle
if "lang" not in st.session_state:
    st.session_state["lang"] = "EN"

col_title, col_lang, col_refresh = st.columns([5, 1, 1])
with col_title:
    if st.session_state["lang"] == "EN":
        st.title("Stock Tracker Dashboard")
    else:
        st.title("股票追踪器")
with col_lang:
    if st.button("🇨🇳 中文" if st.session_state["lang"] == "EN" else "🇺🇸 English"):
        st.session_state["lang"] = "ZH" if st.session_state["lang"] == "EN" else "EN"
        st.rerun()
with col_refresh:
    if st.button("🔄 刷新" if st.session_state["lang"] == "ZH" else "🔄 Refresh"):
        st.rerun()

lang = st.session_state["lang"]

T = {
    "portfolio": {"EN": "Portfolio", "ZH": "投资组合"},
    "scores": {"EN": "Stock Scores", "ZH": "股票评分"},
    "discover": {"EN": "Discover & Watchlist", "ZH": "发现 & 关注列表"},
    "news": {"EN": "News & Company Info", "ZH": "新闻 & 公司信息"},
    "performance": {"EN": "Portfolio Performance", "ZH": "投资组合表现"},
    "refresh": {"EN": "Refresh", "ZH": "刷新"},
    "period": {"EN": "Period", "ZH": "时间段"},
    "filter_ind": {"EN": "Filter by industry", "ZH": "按行业筛选"},
    "invested": {"EN": "Invested", "ZH": "投入"},
    "value": {"EN": "Value", "ZH": "当前价值"},
    "alltime": {"EN": "All-Time Gain", "ZH": "总收益"},
    "positions": {"EN": "Positions", "ZH": "持仓数"},
    "by_ind": {"EN": "By industry", "ZH": "按行业"},
    "sell_remove": {"EN": "Sell or remove", "ZH": "卖出或删除"},
    "position": {"EN": "Position", "ZH": "持仓"},
    "shares_sell": {"EN": "Shares to sell", "ZH": "卖出股数"},
    "sell_price": {"EN": "Sell price (0=current)", "ZH": "卖出价格 (0=当前)"},
    "sell": {"EN": "Sell", "ZH": "卖出"},
    "remove": {"EN": "Remove", "ZH": "删除"},
    "add_position": {"EN": "Add a position", "ZH": "添加持仓"},
    "ticker": {"EN": "Ticker", "ZH": "股票代码"},
    "shares": {"EN": "Shares", "ZH": "股数"},
    "buy_date": {"EN": "Buy Date", "ZH": "购买日期"},
    "buy_price": {"EN": "Buy Price (0=auto)", "ZH": "购买价格 (0=自动)"},
    "add": {"EN": "Add Position", "ZH": "添加持仓"},
    "ratings": {"EN": "Stock Scores & Ratings", "ZH": "股票评分与评级"},
    "watchlist": {"EN": "Full watchlist", "ZH": "完整关注列表"},
    "add_ticker": {"EN": "Add ticker", "ZH": "添加股票代码"},
    "top_picks": {"EN": "Top stock picks", "ZH": "最佳股票推荐"},
    "show": {"EN": "Show", "ZH": "显示"},
    "all_tracked": {"EN": "All tracked", "ZH": "全部追踪"},
    "not_owned": {"EN": "Not in portfolio", "ZH": "未持有"},
    "ratio_analysis": {"EN": "Ratio Analysis", "ZH": "比率分析"},
    "pe": {"EN": "P/E Ratio", "ZH": "市盈率"},
    "roe_label": {"EN": "Return on Equity", "ZH": "净资产收益率"},
    "margin": {"EN": "Profit Margin", "ZH": "利润率"},
    "rev_growth": {"EN": "Revenue Growth", "ZH": "营收增长"},
    "general_market": {"EN": "General market", "ZH": "大盘资讯"},
    "company_profiles": {"EN": "Company Profiles", "ZH": "公司简介"},
    "select_company": {"EN": "Select a company", "ZH": "选择公司"},
    "about": {"EN": "About", "ZH": "关于"},
    "key_stats": {"EN": "Key stats", "ZH": "关键数据"},
    "market_cap": {"EN": "Market Cap", "ZH": "市值"},
    "employees": {"EN": "Employees", "ZH": "员工数"},
    "news_tab": {"EN": "News", "ZH": "新闻"},
    "screener": {"EN": "Screener", "ZH": "筛选器"},
    "company_tab": {"EN": "Company Info", "ZH": "公司信息"},
    "owned": {"EN": "Owned", "ZH": "已持有"},
    "score": {"EN": "Score", "ZH": "评分"},
    "fetching": {"EN": "Fetching data for", "ZH": "正在获取数据"},
    "added": {"EN": "Added", "ZH": "已添加"},
    "sold": {"EN": "Sold. Proceeds", "ZH": "已卖出。收益"},
    "gain": {"EN": "Gain", "ZH": "盈亏"},
    "removed": {"EN": "Removed", "ZH": "已删除"},
    "no_buys": {"EN": "No strong buys right now.", "ZH": "目前没有强烈推荐买入的股票。"},
    "run_scripts": {"EN": "Run the scripts first.", "ZH": "请先运行脚本。"},
    "current_price": {"EN": "Current Price", "ZH": "当前价格"},
}

def t(key):
    return T.get(key, {}).get(lang, key)


tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Portfolio", "Stock Scores", "Discover & Watchlist", "Ratio Analysis", "News & Company Info", "Screener"
])

with tab1:
    portfolio  = load_json(PORTFOLIO_FILE, [])
    industries = load_json(INDUSTRIES_FILE, {})
    ch, cr = st.columns([6, 1])
    ch.subheader("Portfolio Performance")
    if cr.button("Refresh"):
        st.rerun()

    if portfolio:
        period = st.radio("Period", ["1W","1M","3M","6M","YTD","1Y","All"], horizontal=True, index=6)
        ps     = get_period_start(period)
        all_inds = list(set(industries.get(e["ticker"], {}).get("industry", "Other") for e in portfolio))
        sel_inds = st.multiselect("Filter by industry", all_inds, default=all_inds)
        rows = []
        tc = tv = tpc = 0
        for i, entry in enumerate(portfolio):
            t    = entry["ticker"]
            ind  = industries.get(t, {})
            if ind.get("industry", "Other") not in sel_inds:
                continue
            sh   = entry["shares"]
            bp   = entry["buy_price"]
            cost = entry["cost"]
            now  = get_current_price(t) or bp
            bd   = entry["buy_date"]
            if ps and datetime.strptime(bd, "%Y-%m-%d") < ps:
                pbp = get_price_on_date(t, ps.strftime("%Y-%m-%d")) or bp
            else:
                pbp = bp
            pc  = round(sh * pbp, 2)
            val = round(sh * now, 2)
            pg  = round(val - pc, 2)
            pp  = round(pg / pc * 100, 2) if pc else 0
            ag  = round(val - cost, 2)
            ap  = round(ag / cost * 100, 2) if cost else 0
            tc += cost; tv += val; tpc += pc
            rows.append({
                "idx": i, "Ticker": t,
                "Industry": ind.get("industry", "Other"),
                "Shares": sh, "Buy Date": bd,
                "Buy": "$" + str(bp), "Now": "$" + str(now),
                period + " Gain": ("+" if pg >= 0 else "") + "$" + str(abs(pg)),
                period + " %":   ("+" if pp >= 0 else "") + str(abs(pp)) + "%",
                "All-Time":      ("+" if ag >= 0 else "") + "$" + str(abs(ag)) + " (" + str(ap) + "%)",
                "Value": "$" + str(val)
            })

        tpg = round(tv - tpc, 2)
        tpp = round(tpg / tpc * 100, 2) if tpc else 0
        tag = round(tv - tc, 2)
        tap = round(tag / tc * 100, 2) if tc else 0
        c1,c2,c3,c4,c5 = st.columns(5)
        c1.metric("Invested",       "$" + f"{tc:,.2f}")
        c2.metric("Value",          "$" + f"{tv:,.2f}")
        c3.metric(period+" Gain",   "$" + f"{tpg:,.2f}", str(tpp)+"%")
        c4.metric("All-Time Gain",  "$" + f"{tag:,.2f}", str(tap)+"%")
        c5.metric("Positions",      len(rows))

        tickers_p  = list(set(e["ticker"] for e in portfolio))
        shares_map = {e["ticker"]: e["shares"] for e in portfolio}
        p_str = ps.strftime("%Y-%m-%d") if ps else min(e["buy_date"] for e in portfolio)
        cdata = {}
        for t in tickers_p:
            h = yf.Ticker(t).history(start=p_str)
            if not h.empty:
                cdata[t] = h["Close"] * shares_map.get(t, 1)
        if cdata:
            cdf = pd.DataFrame(cdata).ffill()
            cdf["Total"] = cdf.sum(axis=1)
            st.line_chart(cdf["Total"])

        st.subheader("By industry")
        ind_groups = {}
        for row in rows:
            ind_groups.setdefault(row["Industry"], []).append(row)
        for ind_name, ind_rows in ind_groups.items():
            color = industries.get(ind_rows[0]["Ticker"], {}).get("color", "#ccc")
            st.markdown("<span style=\'background:"+color+";padding:2px 10px;border-radius:12px;color:white;font-size:13px\'>"+ind_name+"</span>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(ind_rows).drop(columns=["idx","Industry"]), width="stretch")

        st.subheader("Sell or remove")
        opts = [str(i)+": "+e["ticker"]+" ("+str(e["shares"])+" shares, "+e["buy_date"]+")" for i,e in enumerate(portfolio)]
        sel  = st.selectbox("Position", opts)
        si   = int(sel.split(":")[0])
        c1,c2 = st.columns(2)
        ss = c1.number_input("Shares to sell", min_value=0.01, max_value=float(portfolio[si]["shares"]), value=float(portfolio[si]["shares"]))
        sp = c2.number_input("Sell price (0=current)", min_value=0.0, value=0.0)
        cs, cr2 = st.columns(2)
        with cs:
            if st.button("Sell"):
                e = portfolio[si]
                p = sp if sp > 0 else get_current_price(e["ticker"])
                proceeds = round(ss*p, 2)
                gain     = round(proceeds - ss*e["buy_price"], 2)
                if ss >= e["shares"]:
                    portfolio.pop(si)
                else:
                    portfolio[si]["shares"] = round(e["shares"]-ss, 4)
                    portfolio[si]["cost"]   = round(portfolio[si]["shares"]*e["buy_price"], 2)
                save_json(PORTFOLIO_FILE, portfolio)
                auto_push("Sell position")
                st.success("Sold. Proceeds: $"+str(proceeds)+" Gain: $"+str(gain))
                st.rerun()
        with cr2:
            if st.button("Remove"):
                portfolio.pop(si)
                save_json(PORTFOLIO_FILE, portfolio)
                auto_push("Remove position")
                st.success("Removed")
                st.rerun()

    st.subheader("Add a position")
    c1,c2,c3,c4 = st.columns(4)
    nt  = c1.text_input("Ticker", placeholder="AAPL").upper()
    ns  = c2.number_input("Shares", min_value=0.01, value=1.0)
    nd  = c3.date_input("Buy Date")
    np_ = c4.number_input("Buy Price (0=auto)", min_value=0.0, value=0.0)
    if st.button("Add Position"):
        if nt:
            price = np_ if np_ > 0 else (get_price_on_date(nt, str(nd)) or get_current_price(nt))
            portfolio.append({"ticker":nt,"shares":ns,"buy_date":str(nd),"buy_price":price,"cost":round(ns*price,2)})
            save_json(PORTFOLIO_FILE, portfolio)
            with st.spinner("Fetching data for "+nt+"..."):
                add_to_watchlist(nt)
            st.rerun()

with tab2:
    st.subheader("Stock Scores & Ratings")
    industries = load_json(INDUSTRIES_FILE, {})
    try:
        scores = pd.read_csv("data/scores.csv")
        for _, row in scores.iterrows():
            t    = row["ticker"]
            ind  = industries.get(t, {})
            col  = ind.get("color", "#95A5A6")
            icon = "🟢" if row["rating"] in ["STRONG BUY","BUY"] else "🟡" if row["rating"]=="WATCH" else "🔴"
            label = icon+" "+t+"  —  "+row["rating"]+"  —  Score: "+str(row["score"])+"/85  —  $"+str(row["price"])
            with st.expander(label):
                st.markdown("<span style=\'background:"+col+";padding:2px 10px;border-radius:12px;color:white;font-size:12px\'>"+ind.get("industry","Other")+"</span>", unsafe_allow_html=True)
                st.write("")
                for reason in str(row.get("reasons","")).split(" | "):
                    st.write("• "+reason)
    except FileNotFoundError:
        st.warning("Run score_stocks.py first")

with tab3:
    industries = load_json(INDUSTRIES_FILE, {})
    watchlist  = load_json(WATCHLIST_FILE, [])
    portfolio  = load_json(PORTFOLIO_FILE, [])
    owned      = set(e["ticker"] for e in portfolio)

    with st.expander("Full watchlist ("+str(len(watchlist))+" stocks)"):
        if watchlist:
            cols = st.columns(4)
            for i, t in enumerate(watchlist):
                ind = industries.get(t, {})
                with cols[i % 4]:
                    color = ind.get("color","#95A5A6")
                    label = ind.get("industry","Other")
                    st.markdown("**"+t+"**<br><span style=\'background:"+color+";padding:1px 6px;border-radius:8px;color:white;font-size:11px\'>"+label+"</span>", unsafe_allow_html=True)
                    if st.button("Remove", key="wl_rm_"+t):
                        watchlist.remove(t)
                        save_json(WATCHLIST_FILE, watchlist)
                        st.rerun()
        st.markdown("---")
        wc1, wc2 = st.columns([3,1])
        nwt = wc1.text_input("Add ticker", placeholder="TSLA", key="wl_add").upper()
        if wc2.button("Add", key="wl_btn"):
            if nwt and nwt not in watchlist:
                st.session_state["fetching"] = nwt

if st.session_state.get("fetching"):
    nwt = st.session_state["fetching"]
    st.info("Fetching data for "+nwt+"...")
    add_to_watchlist(nwt)
    st.session_state["fetching"] = None
    st.rerun()

    st.subheader("Top stock picks")
    mode = st.radio("Show", ["All tracked","Not in portfolio"], horizontal=True)
    try:
        scores = pd.read_csv("data/scores.csv")
        ratios = pd.read_csv("data/calculated_ratios.csv")
        merged = scores.merge(ratios, on="ticker", how="left")
        merged["industry"] = merged["ticker"].map(lambda t: industries.get(t,{}).get("industry","Other"))
        merged["color"]    = merged["ticker"].map(lambda t: industries.get(t,{}).get("color","#95A5A6"))
        if mode == "Not in portfolio":
            merged = merged[~merged["ticker"].isin(owned)]
        top = merged[merged["rating"].isin(["STRONG BUY","BUY"])].sort_values("score",ascending=False).head(10)
        if top.empty:
            st.info("No strong buys right now.")
        else:
            for _, row in top.iterrows():
                t    = row["ticker"]
                icon = "🟢" if row["rating"]=="STRONG BUY" else "🟡"
                tag  = " - Owned" if t in owned else ""
                pv   = row.get("price_x", row.get("price",""))
                with st.expander(icon+" "+t+"  —  "+row["rating"]+"  —  Score: "+str(row["score"])+"/85  —  $"+str(pv)+tag):
                    color = row["color"]
                    st.markdown("<span style=\'background:"+color+";padding:2px 10px;border-radius:12px;color:white;font-size:12px\'>"+row["industry"]+"</span>", unsafe_allow_html=True)
                    st.write("")
                    for reason in str(row.get("reasons","")).split(" | "):
                        st.write("• "+reason)
                    rc1,rc2,rc3,rc4,rc5 = st.columns(5)
                    pe  = round(row["pe_ratio"],1)          if pd.notna(row.get("pe_ratio"))       else "N/A"
                    roe = str(round(row["roe"]*100,1))+"%"  if pd.notna(row.get("roe"))            else "N/A"
                    pm  = str(round(row["profit_margin"]*100,1))+"%" if pd.notna(row.get("profit_margin")) else "N/A"
                    de  = round(row["debt_to_equity"],2)    if pd.notna(row.get("debt_to_equity")) else "N/A"
                    rg  = str(round(row["revenue_growth"]*100,1))+"%" if pd.notna(row.get("revenue_growth")) else "N/A"
                    rc1.metric("P/E", pe); rc2.metric("ROE", roe); rc3.metric("Margin", pm)
                    rc4.metric("D/E", de); rc5.metric("Rev Growth", rg)
    except FileNotFoundError:
        st.warning("Run the scripts first.")

with tab4:
    st.subheader("Ratio Analysis")
    industries = load_json(INDUSTRIES_FILE, {})
    try:
        ratios = pd.read_csv("data/calculated_ratios.csv")
        ratios["Industry"] = ratios["ticker"].map(lambda t: industries.get(t,{}).get("industry","Other"))
        st.dataframe(ratios, width="stretch")
        c1,c2 = st.columns(2)
        with c1:
            st.subheader("P/E Ratio")
            pe = ratios[ratios["pe_ratio"]>0].sort_values("pe_ratio")
            st.bar_chart(pe.set_index("ticker")["pe_ratio"])
        with c2:
            st.subheader("Return on Equity")
            roe = ratios[ratios["roe"].notna()].sort_values("roe",ascending=False)
            st.bar_chart(roe.set_index("ticker")["roe"])
        c3,c4 = st.columns(2)
        with c3:
            st.subheader("Profit Margin")
            pm = ratios[ratios["profit_margin"].notna()].sort_values("profit_margin",ascending=False)
            st.bar_chart(pm.set_index("ticker")["profit_margin"])
        with c4:
            st.subheader("Revenue Growth")
            rg = ratios[ratios["revenue_growth"].notna()].sort_values("revenue_growth",ascending=False)
            st.bar_chart(rg.set_index("ticker")["revenue_growth"])
    except FileNotFoundError:
        st.warning("Run calculate_ratios.py first")

with tab5:
    news_tab, company_tab = st.tabs(["News","Company Info"])
    with news_tab:
        st.markdown("### General market")
        for item in get_news("stock market today", num=2):
            st.markdown("["+item["title"]+"]("+item["link"]+") — *"+item["date"]+"*")
        st.markdown("---")
        industries  = load_json(INDUSTRIES_FILE, {})
        tickers_all = all_tickers()
        ind_map = {}
        for t in tickers_all:
            ind = industries.get(t,{}).get("industry","Other")
            ind_map.setdefault(ind,[]).append(t)
        for ind_name, tickers_in_ind in ind_map.items():
            color = industries.get(tickers_in_ind[0],{}).get("color","#ccc")
            st.markdown("<span style=\'background:"+color+";padding:2px 10px;border-radius:12px;color:white;font-size:13px\'>"+ind_name+" — "+", ".join(tickers_in_ind)+"</span>", unsafe_allow_html=True)
            for item in get_news(ind_name+" stocks news", num=5):
                st.markdown("["+item["title"]+"]("+item["link"]+") — *"+item["date"]+"*")
            st.markdown("---")
    with company_tab:
        st.subheader("Company Profiles")
        tickers_all = sorted(all_tickers())
        industries  = load_json(INDUSTRIES_FILE, {})
        sel = st.selectbox("Select a company", tickers_all)
        if sel:
            info      = yf.Ticker(sel).info
            name      = info.get("longName", sel)
            about     = info.get("longBusinessSummary","No description available.")
            sector    = info.get("sector","")
            ind_label = info.get("industry","")
            website   = info.get("website","")
            ind_info  = industries.get(sel, {})
            col_      = ind_info.get("color","#95A5A6")
            c1,c2 = st.columns([3,1])
            with c1:
                st.markdown("## "+name+" ("+sel+")")
                if sector:
                    st.markdown("<span style=\'background:"+col_+";padding:2px 10px;border-radius:12px;color:white;font-size:13px\'>"+sector+" — "+ind_label+"</span>", unsafe_allow_html=True)
                if website:
                    st.markdown("["+website+"]("+website+")")
            with c2:
                p = get_current_price(sel)
                if p:
                    st.metric("Current Price","$"+str(p))
            st.markdown("---")
            st.markdown("**About**")
            st.write(about)
            st.markdown("---")
            st.markdown("**Key stats**")
            s1,s2,s3,s4 = st.columns(4)
            mc = info.get("marketCap")
            s1.metric("Market Cap","$"+f"{mc/1e9:.1f}B" if mc else "N/A")
            emp = info.get("fullTimeEmployees")
            s2.metric("Employees",f"{emp:,}" if emp else "N/A")
            s3.metric("52W High","$"+str(info.get("fiftyTwoWeekHigh","N/A")))
            s4.metric("52W Low","$"+str(info.get("fiftyTwoWeekLow","N/A")))

with tab6:
    st.subheader("🔍 Undervalued Stock Screener")
    st.caption("Scans 100+ stocks and surfaces the most undervalued ones not already in your portfolio or watchlist.")

    col_run, col_n = st.columns([1, 1])
    num_results = col_n.slider("How many to show", 5, 20, 10)

    if col_run.button("🔄 Run Screener Now"):
        with st.spinner("Scanning 100+ stocks... this takes 2-3 minutes"):
            import subprocess, sys
            subprocess.run([sys.executable, "scripts/screener.py"])
        st.rerun()

    try:
        df = pd.read_csv("data/screener.csv")
        top = df.head(num_results)

        st.markdown("---")
        st.markdown("### Top picks right now")

        for _, row in top.iterrows():
            ticker  = row["ticker"]
            score   = row["score"]
            price   = row["price"]
            sector  = row["sector"]
            name    = row["name"]
            reasons = str(row.get("reasons", "")).split(" | ")

            icon = "🟢" if score >= 70 else "🟡" if score >= 50 else "🔵"
            with st.expander(icon + " " + ticker + "  —  " + name + "  —  Score: " + str(score) + "/95  —  $" + str(price)):
                st.markdown("**Sector:** " + sector)
                st.write("")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("P/E",          str(row["pe"]))
                c2.metric("ROE",          str(row["roe"]) + "%")
                c3.metric("Profit Margin",str(row["margin"]) + "%")
                c4.metric("Rev Growth",   str(row["growth"]) + "%")
                c5.metric("PEG",          str(row["peg"]))
                st.write("")
                st.markdown("**Why it scores well:**")
                for r in reasons:
                    if r.strip():
                        st.write("• " + r.strip())

                if st.button("➕ Add to watchlist", key="scr_add_" + ticker):
                    wl = load_json(WATCHLIST_FILE, [])
                    if ticker not in wl:
                        with st.spinner("Adding " + ticker + "..."):
                            add_to_watchlist(ticker)
                        st.success("Added " + ticker + " to watchlist!")
                        st.rerun()

        st.markdown("---")
        st.caption("Last updated: " + str(pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")))

    except FileNotFoundError:
        st.info("Click Run Screener Now to find undervalued stocks.")
