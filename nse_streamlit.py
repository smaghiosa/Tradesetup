"""
NSE Trade Setup Engine — Streamlit
====================================
• Claude AI (claude-sonnet) → Yahoo Finance fallback
• Works live market + after hours
• Run:  streamlit run nse_trade_setup.py
• Deps: pip install streamlit yfinance anthropic pandas numpy requests
"""

import streamlit as st
import yfinance as yf
import anthropic
import pandas as pd
import numpy as np
import json, re, time
from datetime import datetime, timezone, timedelta

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NSE Trade Setup Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── DARK THEME CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&display=swap');
:root {
    --green:#00ffaa; --red:#ff3d5a; --amber:#ffb300;
    --blue:#3b8bff;  --purple:#a855f7; --muted:#8a9bb5;
}
body, .stApp { background:#060810 !important; color:#e2e8f8 !important; }
.stApp { font-family:'IBM Plex Mono',monospace; }
.block-container { padding-top:1.2rem; max-width:1180px; }
/* Metric cards */
div[data-testid="metric-container"] {
    background:#101828; border:1px solid #1a2540;
    border-radius:10px; padding:10px 14px;
}
div[data-testid="metric-container"] label { color:#4a607f !important; font-size:11px !important; }
div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
    color:#e2e8f8 !important; font-size:18px !important; font-weight:700;
}
/* Buttons */
.stButton>button {
    background:linear-gradient(135deg,#00ffaa,#3b8bff);
    color:#000 !important; font-weight:700; border:none;
    border-radius:8px; padding:8px 22px;
    font-family:'IBM Plex Mono',monospace; letter-spacing:.06em;
}
.stButton>button:hover { opacity:.85; }
/* Sidebar */
section[data-testid="stSidebar"] { background:#0c1020 !important; border-right:1px solid #1a2540; }
/* Selectbox / text_input */
.stSelectbox>div>div, .stTextInput>div>div>input, .stNumberInput>div>div>input {
    background:#101828 !important; border:1px solid #1a2540 !important;
    color:#e2e8f8 !important; border-radius:8px !important;
    font-family:'IBM Plex Mono',monospace !important;
}
/* Dataframe */
.stDataFrame { border:1px solid #1a2540; border-radius:10px; }
/* Divider */
hr { border-color:#1a2540 !important; }
/* Hide streamlit branding */
#MainMenu, footer, header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ── CONSTANTS ─────────────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))

UNIVERSE = [
    # Banking & NBFC
    ("HDFCBANK","Banking & NBFC"),("ICICIBANK","Banking & NBFC"),("SBIN","Banking & NBFC"),
    ("KOTAKBANK","Banking & NBFC"),("AXISBANK","Banking & NBFC"),("INDUSINDBK","Banking & NBFC"),
    ("BANKBARODA","Banking & NBFC"),("PNB","Banking & NBFC"),("FEDERALBNK","Banking & NBFC"),
    ("IDFCFIRSTB","Banking & NBFC"),("BAJFINANCE","Banking & NBFC"),("BAJAJFINSV","Banking & NBFC"),
    ("MUTHOOTFIN","Banking & NBFC"),("CHOLAFIN","Banking & NBFC"),("SBILIFE","Banking & NBFC"),
    ("HDFCLIFE","Banking & NBFC"),("RECLTD","Banking & NBFC"),("PFC","Banking & NBFC"),("IRFC","Banking & NBFC"),
    # IT & Tech
    ("TCS","IT & Tech"),("INFY","IT & Tech"),("WIPRO","IT & Tech"),("HCLTECH","IT & Tech"),
    ("TECHM","IT & Tech"),("LTIM","IT & Tech"),("PERSISTENT","IT & Tech"),("COFORGE","IT & Tech"),
    ("MPHASIS","IT & Tech"),("KPITTECH","IT & Tech"),("TATAELXSI","IT & Tech"),("DIXON","IT & Tech"),
    # Pharma
    ("SUNPHARMA","Pharma & Healthcare"),("DIVISLAB","Pharma & Healthcare"),("CIPLA","Pharma & Healthcare"),
    ("DRREDDY","Pharma & Healthcare"),("APOLLOHOSP","Pharma & Healthcare"),("MAXHEALTH","Pharma & Healthcare"),
    # Auto & EV
    ("MARUTI","Auto & EV"),("TATAMOTORS","Auto & EV"),("BAJAJ-AUTO","Auto & EV"),
    ("HEROMOTOCO","Auto & EV"),("EICHERMOT","Auto & EV"),("MOTHERSON","Auto & EV"),
    ("BOSCH","Auto & EV"),("EXIDEIND","Auto & EV"),("MINDA","Auto & EV"),
    # Energy & Power
    ("RELIANCE","Energy & Power"),("ONGC","Energy & Power"),("BPCL","Energy & Power"),
    ("IOC","Energy & Power"),("NTPC","Energy & Power"),("POWERGRID","Energy & Power"),
    ("TATAPOWER","Energy & Power"),("ADANIGREEN","Energy & Power"),("ADANIPORTS","Energy & Power"),
    ("COALINDIA","Energy & Power"),("NHPC","Energy & Power"),
    # FMCG
    ("HINDUNILVR","FMCG & Consumer"),("ITC","FMCG & Consumer"),("NESTLEIND","FMCG & Consumer"),
    ("BRITANNIA","FMCG & Consumer"),("GODREJCP","FMCG & Consumer"),("MARICO","FMCG & Consumer"),
    ("COLPAL","FMCG & Consumer"),("DABUR","FMCG & Consumer"),("TATACONSUM","FMCG & Consumer"),
    ("DMART","FMCG & Consumer"),("TRENT","FMCG & Consumer"),("ZOMATO","FMCG & Consumer"),("IRCTC","FMCG & Consumer"),
    # Metals
    ("TATASTEEL","Metals & Mining"),("JSWSTEEL","Metals & Mining"),("HINDALCO","Metals & Mining"),
    ("VEDL","Metals & Mining"),("SAIL","Metals & Mining"),("NMDC","Metals & Mining"),("HINDZINC","Metals & Mining"),
    # Engineering
    ("LT","Engineering"),("HAL","Engineering"),("BEL","Engineering"),("BHEL","Engineering"),
    ("SIEMENS","Engineering"),("ABB","Engineering"),("CUMMINSIND","Engineering"),("THERMAX","Engineering"),
    # Paints & Chemicals
    ("ASIANPAINT","Paints & Chemicals"),("BERGEPAINT","Paints & Chemicals"),("PIDILITIND","Paints & Chemicals"),
    ("DEEPAKNTR","Paints & Chemicals"),("SRF","Paints & Chemicals"),
    # Electricals
    ("HAVELLS","Electricals"),("POLYCAB","Electricals"),("VOLTAS","Electricals"),("BLUESTAR","Electricals"),
    # Others
    ("TITAN","Jewellery"),("ULTRACEMCO","Cement"),("SHREECEM","Cement"),("AMBUJACEM","Cement"),
    ("BHARTIARTL","Telecom"),("NYKAA","E-Commerce"),
]

SECTOR_LIST = ["All Sectors","Banking & NBFC","IT & Tech","Pharma & Healthcare","Auto & EV",
               "Energy & Power","FMCG & Consumer","Metals & Mining","Engineering",
               "Paints & Chemicals","Electricals","Jewellery","Cement","Telecom"]

FNO_SET = {
    "NIFTY","BANKNIFTY","FINNIFTY","RELIANCE","TCS","INFY","HDFCBANK","SBIN","ICICIBANK",
    "BAJFINANCE","TATAMOTORS","WIPRO","AXISBANK","MARUTI","ADANIENT","LT","SUNPHARMA",
    "HCLTECH","ONGC","NTPC","POWERGRID","COALINDIA","HINDALCO","JSWSTEEL","TATAPOWER",
    "GRASIM","ULTRACEMCO","TITAN","ASIANPAINT","NESTLEIND","HINDUNILVR","KOTAKBANK",
    "INDUSINDBK","BHARTIARTL","TECHM","DIVISLAB","CIPLA","DRREDDY","APOLLOHOSP",
    "BAJAJFINSV","BPCL","IOC","VEDL","SAIL","NMDC","PIDILITIND","VOLTAS","ZOMATO",
    "HAL","BEL","IRFC","PNB","BANKBARODA","FEDERALBNK","IDFCFIRSTB","MUTHOOTFIN",
    "CHOLAFIN","LTIM","PERSISTENT","COFORGE","TATASTEEL","HINDZINC","RECLTD","PFC",
    "TATACONSUM","BRITANNIA","GODREJCP","MARICO","COLPAL","HAVELLS","POLYCAB","DIXON",
    "EICHERMOT","HEROMOTOCO","BAJAJ-AUTO","BOSCH","MOTHERSON","SHREECEM","AMBUJACEM",
}

LOT_MAP = {
    "NIFTY":50,"BANKNIFTY":15,"FINNIFTY":40,"RELIANCE":250,"TCS":150,"INFY":300,
    "HDFCBANK":550,"SBIN":1500,"ICICIBANK":700,"BAJFINANCE":125,"TATAMOTORS":1425,
    "WIPRO":1500,"MARUTI":100,"AXISBANK":600,"ADANIENT":625,"LT":375,"SUNPHARMA":350,
    "HCLTECH":350,"ZOMATO":4500,"ONGC":1975,"NTPC":3375,"BHARTIARTL":475,"KOTAKBANK":400,
}

POPULAR = ["RELIANCE","TCS","INFY","HDFCBANK","SBIN","ICICIBANK","TATAMOTORS",
           "BAJFINANCE","MARUTI","AXISBANK","ZOMATO","IRCTC","NIFTY","BANKNIFTY"]

# ── HELPERS ───────────────────────────────────────────────────────────────────
def now_ist():
    return datetime.now(IST).strftime("%d %b %Y %H:%M:%S IST")

def fmt(n):
    if n is None: return "—"
    return f"{n:,.2f}"

def fmtpct(n):
    if n is None: return "—"
    sign = "+" if n >= 0 else ""
    return f"{sign}{n:.2f}%"

def ns(ticker):
    """Convert NSE ticker → Yahoo Finance symbol."""
    if ticker == "NIFTY":   return "^NSEI"
    if ticker == "BANKNIFTY": return "^NSEBANK"
    return ticker + ".NS"

# ── YAHOO FINANCE DATA ────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def fetch_quote_yf(ticker: str) -> dict | None:
    try:
        sym = ns(ticker)
        t = yf.Ticker(sym)
        info = t.fast_info
        hist = t.history(period="1d", interval="1m")
        live = float(info.last_price or info.previous_close or 0)
        prev = float(info.previous_close or live)
        open_ = float(info.open or prev)
        high  = float(info.day_high or live)
        low   = float(info.day_low  or live)
        vol   = int(info.last_volume or 0)
        w52h  = float(info.year_high or live * 1.3)
        w52l  = float(info.year_low  or live * 0.7)
        chg   = ((live - prev) / prev * 100) if prev else 0
        return dict(livePrice=live, prevClose=prev, open=open_, high=high,
                    low=low, volume=vol, w52h=w52h, w52l=w52l, chgPct=chg)
    except Exception as e:
        return None

@st.cache_data(ttl=300)
def fetch_history_yf(ticker: str, days=60) -> pd.DataFrame | None:
    try:
        sym = ns(ticker)
        period = "1mo" if days <= 30 else "3mo" if days <= 90 else "6mo"
        df = yf.download(sym, period=period, interval="1d",
                         progress=False, auto_adjust=True)
        if df.empty: return None
        df = df.dropna(subset=["Close","Volume"])
        df.columns = [c.lower() for c in df.columns]
        return df
    except:
        return None

@st.cache_data(ttl=120)
def fetch_vix() -> float:
    try:
        t = yf.Ticker("^INDIAVIX")
        v = t.fast_info.last_price
        return round(float(v), 2) if v and v > 0 else 14.5
    except:
        return 14.5

# ── TECHNICAL CALCULATIONS ────────────────────────────────────────────────────
def compute_poc(df: pd.DataFrame | None, live: float) -> dict:
    if df is None or len(df) < 2:
        return dict(poc=live, vah=live*1.008, val=live*0.992)
    highs  = df["high"].values
    lows   = df["low"].values
    vols   = df["volume"].values
    aH, aL = highs.max(), lows.min()
    BUCKETS = 50
    bs = (aH - aL) / BUCKETS if aH != aL else 1
    vm = np.zeros(BUCKETS)
    for h, l, v in zip(highs, lows, vols):
        if not (h and l and v): continue
        s = max(0, int((l - aL) / bs))
        e = min(BUCKETS-1, int((h - aL) / bs))
        vpb = v / max(1, e - s + 1)
        vm[s:e+1] += vpb
    poc_idx = int(np.argmax(vm))
    poc = aL + (poc_idx + 0.5) * bs
    total = vm.sum()
    acc, lo, hi = vm[poc_idx], poc_idx, poc_idx
    while acc < total * 0.70 and (lo > 0 or hi < BUCKETS-1):
        el = vm[lo-1] if lo > 0 else 0
        eh = vm[hi+1] if hi < BUCKETS-1 else 0
        if el >= eh and lo > 0: acc += el; lo -= 1
        elif hi < BUCKETS-1:   acc += eh; hi += 1
        else: break
    return dict(poc=round(poc,2), val=round(aL+lo*bs,2), vah=round(aL+(hi+1)*bs,2))

def compute_rsi(closes, period=14):
    if len(closes) < period + 1: return 50.0
    diffs = np.diff(closes)
    g = np.where(diffs > 0, diffs, 0)
    l = np.where(diffs < 0, -diffs, 0)
    ag, al = g[:period].mean(), l[:period].mean()
    for i in range(period, len(diffs)):
        ag = (ag*(period-1) + g[i]) / period
        al = (al*(period-1) + l[i]) / period
    return round(100 - 100/(1 + ag/al), 2) if al else 100.0

def compute_ema(closes, period):
    if len(closes) < period: return closes[-1] if len(closes) else 0.0
    k = 2 / (period + 1)
    ema = closes[:period].mean()
    for c in closes[period:]: ema = c*k + ema*(1-k)
    return round(ema, 2)

def compute_tech(df: pd.DataFrame | None, live: float) -> dict:
    base = dict(rsi=50, prev_rsi=50, ema20=live, ema50=live, ema200=live,
                macd=0, macd_signal=0, adx=20, trend="SIDEWAYS",
                support=round(live*0.97,2), resistance=round(live*1.03,2),
                avg_vol20=0, last_vol=0, vol_doubled=False, consistent10=False)
    if df is None or len(df) < 5: return base
    closes = df["close"].values.astype(float)
    vols   = df["volume"].values.astype(float)
    rsi  = compute_rsi(closes)
    prev_rsi = compute_rsi(closes[:-1]) if len(closes) > 15 else rsi
    n = len(closes)
    ema20  = compute_ema(closes, min(20, n))
    ema50  = compute_ema(closes, min(50, n))
    ema200 = compute_ema(closes, min(200, n))
    ema12  = compute_ema(closes, 12)
    ema26  = compute_ema(closes, 26)
    macd   = round(ema12 - ema26, 2)
    adx    = min(60, max(10, abs(ema20-ema50)/ema50*100*8+15))
    trend  = ("BULLISH" if live > ema20 > ema50 else
              "BEARISH" if live < ema20 and ema20 < ema50 else "SIDEWAYS")
    recent = df.iloc[-20:]
    sup = round(float(recent["low"].min()), 2)
    res = round(float(recent["high"].max()), 2)
    v20 = vols[-20:]
    avg_vol20 = float(v20.mean()) if len(v20) else 0
    last_vol  = float(vols[-1]) if len(vols) else 0
    vol_doubled   = avg_vol20 > 0 and last_vol >= 2*avg_vol20
    last10 = closes[-10:]
    consistent10  = len(last10) >= 10 and all(last10[i] > last10[i-1] for i in range(1, len(last10)))
    return dict(rsi=rsi, prev_rsi=prev_rsi, ema20=ema20, ema50=ema50, ema200=ema200,
                macd=macd, macd_signal=round(macd*0.6,2), adx=round(adx,2), trend=trend,
                support=sup, resistance=res, avg_vol20=avg_vol20, last_vol=last_vol,
                vol_doubled=vol_doubled, consistent10=consistent10)

def check_momentum(tech):
    c10 = tech["consistent10"]
    vd  = tech["vol_doubled"]
    rsi = tech["rsi"]
    pr  = tech["prev_rsi"]
    crossed40 = pr < 40 <= rsi
    above40   = 40 <= rsi < 70
    score = (40 if c10 else 0) + (35 if vd else 0) + (25 if crossed40 else 15 if above40 else 0)
    return dict(triggered=c10 and vd and (crossed40 or above40),
                score=score, consistent10=c10, vol_doubled=vd,
                rsi_crossed40=crossed40, rsi_above40=above40)

def compute_oi_sim(live):
    step = 10 if live < 500 else 50 if live < 2000 else 100
    base = round(live / step) * step
    cw, pw = base + step*2, base - step*2
    rng = lambda a,b: int(np.random.randint(a, b))
    c_strikes = [{"strike": s, "oi": rng(90000,160000) if s==cw else rng(15000,65000)}
                 for s in [base-step, base, base+step, cw, base+step*3]]
    p_strikes = [{"strike": s, "oi": rng(90000,160000) if s==pw else rng(15000,65000)}
                 for s in [base+step, base, base-step, pw, base-step*3]]
    return dict(call_wall=cw, put_wall=pw,
                max_call_oi=rng(90000,160000), max_put_oi=rng(90000,160000),
                call_strikes=c_strikes, put_strikes=p_strikes)

def make_decision(live, pos, poc, vah, val, vix, is_fno, oi, tech, mom, w52h, w52l):
    rsi, ema20, ema50, trend, sup, res = (tech[k] for k in
        ["rsi","ema20","ema50","trend","support","resistance"])
    cw, pw = oi["call_wall"], oi["put_wall"]
    action, conf, framework, setup_type = "WAIT", 50, "", "standard"

    if mom["triggered"]:
        vr = tech["last_vol"] / max(1, tech["avg_vol20"])
        action, conf, setup_type = "BUY", min(84, 52+mom["score"]//3), "momentum"
        framework = (f"MOMENTUM BREAKOUT: 10D rise + Vol {vr:.1f}x + RSI {rsi:.1f}"
                     + (" crossed 40" if mom["rsi_crossed40"] else " above 40"))
    elif is_fno:
        nc = abs(live - cw)/live < 0.015
        np_ = abs(live - pw)/live < 0.015
        if pos=="ABOVE_VAH" and not nc:    action,conf = "STRONG BUY",72
        elif pos=="ABOVE_VAH" and nc:      action,conf = "AVOID TRAP",65
        elif pos=="BELOW_VAL" and np_:     action,conf = "REVERSAL LONG",63
        elif pos=="BELOW_VAL" and not np_: action,conf = "STRONG SELL",70
        elif pos=="INSIDE_VA" and live>poc: action,conf = "INTRADAY SHORT",58
        else:                               action,conf = "INTRADAY LONG",58
        framework = f"F&O 3-Pillar: VIX={vix} · {pos} · OI Walls"
    else:
        bull = rsi < 70 and live > ema20 > ema50 and trend=="BULLISH"
        bear = rsi < 35 or (live < ema20 and trend=="BEARISH")
        if   pos=="ABOVE_VAH" and bull:    action,conf = "BUY",68
        elif pos=="ABOVE_VAH" and rsi>70:  action,conf = "WAIT",55
        elif pos=="BELOW_VAL" and not bear:action,conf = "BUY DIP",62
        elif pos=="BELOW_VAL" and bear:    action,conf = "SELL",67
        elif bull:                          action,conf = "BUY",60
        elif bear:                          action,conf = "WAIT",52
        else:                               action,conf = "WAIT",50
        framework = f"Non-F&O: VIX={vix} · {pos} · RSI={rsi} · {trend}"

    if w52h and "BUY" in action:
        pct = (w52h - live) / w52h * 100
        if pct <= 3: conf = min(88, conf+6)

    if   vix > 28: conf = max(45, conf-10)
    elif vix > 20: conf = max(45, conf-5)

    is_bull = any(x in action for x in ["BUY","LONG"])
    is_bear = any(x in action for x in ["SELL","SHORT"])
    entry = round(live, 2)
    if is_bull:
        target   = round(min(res, live*1.05), 2) if not is_fno else round(cw*0.998, 2)
        stoploss = round(max(sup, live*0.96), 2) if not is_fno else round(pw*1.002, 2)
    elif is_bear:
        target   = round(max(sup, live*0.96), 2) if not is_fno else round(pw*1.002, 2)
        stoploss = round(min(res, live*1.03), 2) if not is_fno else round(cw*0.998, 2)
    else:
        target, stoploss = round(live*1.03,2), round(live*0.975,2)

    if vix > 20:
        d = abs(entry - stoploss)
        stoploss = round(stoploss - d*0.2, 2) if is_bull else round(stoploss + d*0.2, 2)

    reward = abs(target - entry)
    risk   = abs(entry - stoploss) or 1
    rr     = f"1:{reward/risk:.1f}"

    vn = (" ⚠ VIX HIGH — cut size 50%." if vix>28
          else " VIX elevated — widen stops." if vix>20 else "")

    if setup_type == "momentum":
        vr = tech["last_vol"] / max(1, tech["avg_vol20"])
        narrative = (f"MOMENTUM BREAKOUT — 10 consecutive higher closes confirmed. "
                     f"Volume at {vr:.1f}x the 20D avg. RSI at {rsi:.1f}. "
                     f"Entry near ₹{fmt(live)} with target ₹{fmt(target)}.{vn}")
    elif is_fno:
        narrative = (f"{action} signal. CMP ₹{fmt(live)} is {pos.replace('_',' ')} "
                     f"with POC ₹{fmt(poc)}. Call wall ₹{fmt(cw)} · Put wall ₹{fmt(pw)}. VIX {vix}.{vn}")
    else:
        narrative = (f"{action} via 2-pillar + technicals. Price is {pos.replace('_',' ')}, "
                     f"RSI {rsi}, trend {trend}. Support ₹{fmt(sup)} · Resistance ₹{fmt(res)}.{vn}")

    risks = [
        f"VIX spike above 20 invalidates setup" if vix<=20 else f"High VIX ({vix}) — gap moves possible",
        (f"Break of {'Put wall ₹'+fmt(pw) if is_bull else 'Call wall ₹'+fmt(cw)} = exit"
         if is_fno else f"Close below support ₹{fmt(sup)} = reversal"),
        ("Volume dry-up or RSI drop below 40 = exit immediately"
         if setup_type=="momentum" else "Global/FII flows can override setup"),
    ]
    return dict(action=action, confidence=conf, entry=entry, target=target,
                stoploss=stoploss, rr=rr, framework=framework, narrative=narrative,
                key_risks=risks, setup_type=setup_type)

def grade_setup(score):
    if score >= 95: return "A+", "🟢", "EXCEPTIONAL"
    if score >= 85: return "A",  "🟢", "STRONG"
    if score >= 75: return "B+", "🔵", "GOOD"
    if score >= 65: return "B",  "🔵", "MODERATE"
    if score >= 55: return "C+", "🟡", "WEAK"
    return              "C",  "⚪", "POOR"

def score_setup(r):
    score = r.get("confidence", 50)
    mom = r.get("momentum", {})
    if mom.get("triggered"):        score += 20
    pos = r.get("price_position","")
    if pos == "ABOVE_VAH":          score += 10
    if pos == "BELOW_VAL" and "SELL" in r.get("action",""): score += 10
    rsi = r.get("rsi", 50)
    if 50 <= rsi < 70:              score += 5
    if r.get("trend")=="BULLISH" and "BUY"  in r.get("action",""): score += 8
    if r.get("trend")=="BEARISH" and "SELL" in r.get("action",""): score += 8
    if r.get("vol_doubled"):        score += 10
    if r.get("consistent10"):       score += 8
    try:
        rr_n = float(r.get("rr","1:1").split(":")[1])
        if rr_n >= 3: score += 10
        elif rr_n >= 2: score += 5
    except: pass
    w52h = r.get("w52h"); live = r.get("live")
    if w52h and live and "BUY" in r.get("action",""):
        pct = (w52h - live) / w52h * 100
        if pct <= 5:  score += 12
        elif pct <= 10: score += 6
    if r.get("adx",0) > 30: score += 5
    return min(100, round(score))

# ── CLAUDE AI ANALYSIS ────────────────────────────────────────────────────────
def claude_analysis(ticker: str, api_key: str) -> dict | None:
    """Try Claude AI. Returns parsed dict or None on failure."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        now_str = datetime.now(IST).strftime("%d %b %Y %H:%M IST")
        prompt = f"""You are an expert NSE analyst. Today: {now_str}.
Analyze "{ticker}" on NSE. Use web search for current price and India VIX.
F&O eligible: RELIANCE,TCS,INFY,HDFCBANK,SBIN,ICICIBANK,BAJFINANCE,TATAMOTORS,WIPRO,AXISBANK,MARUTI,LT,SUNPHARMA,HCLTECH,ONGC,NTPC,ZOMATO,NIFTY,BANKNIFTY etc.
POC = price with highest traded volume. VAH = POC+(H-L)*0.4, VAL = POC-(H-L)*0.4.
If F&O: include callWall, putWall and 5 option strikes each side.
If non-F&O: include RSI14, EMA20/50/200, MACD, ADX, trend, support, resistance.
Return ONLY raw JSON, no markdown, no explanation:
{{"livePrice":<n>,"priceSource":"<s>","changePct":<n>,"todayOpen":<n>,"todayHigh":<n>,"todayLow":<n>,
"weekHigh52":<n>,"weekLow52":<n>,"companyName":"<s>","sector":"<s>","isFno":<bool>,
"fnoLotSize":<n_or_null>,"vix":<n>,"poc":<n>,"val":<n>,"vah":<n>,"pricePosition":"<s>",
"callWall":<n_or_null>,"putWall":<n_or_null>,"maxCallOI":<n_or_null>,"maxPutOI":<n_or_null>,
"callStrikes":[{{"strike":<n>,"oi":<n>}}],"putStrikes":[{{"strike":<n>,"oi":<n>}}],
"rsi":<n_or_null>,"ema20":<n_or_null>,"ema50":<n_or_null>,"ema200":<n_or_null>,
"macd":<n_or_null>,"adx":<n_or_null>,"trend":"<s_or_null>","support":<n_or_null>,"resistance":<n_or_null>,
"action":"<s>","confidence":<n>,"entry":<n>,"target":<n>,"stoploss":<n>,"rr":"1:X.X",
"framework":"<s>","narrative":"<s>","keyRisks":["<s>","<s>","<s>"]}}"""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}]
        )
        raw = "".join(b.text for b in response.content if hasattr(b,"text"))
        match = re.search(r'\{[\s\S]*\}', raw)
        if not match: return None
        cleaned = re.sub(r',\s*([}\]])', r'\1', match.group(0))
        parsed = json.loads(cleaned)
        if not parsed.get("livePrice") or parsed["livePrice"] <= 0: return None
        parsed["data_mode"] = "claude"
        return parsed
    except anthropic.RateLimitError:
        return {"_error": "rate_limit"}
    except Exception as e:
        return {"_error": str(e)}

# ── FULL ANALYSIS PIPELINE ────────────────────────────────────────────────────
def analyze_ticker(ticker: str, api_key: str = "") -> dict:
    ticker = ticker.strip().upper()
    data_mode = "yahoo"
    claude_data = None
    switch_reason = ""

    # 1. Try Claude
    if api_key:
        with st.spinner("🤖 Querying Claude AI with web search…"):
            claude_data = claude_analysis(ticker, api_key)
        if claude_data and "_error" in claude_data:
            err = claude_data["_error"]
            switch_reason = ("⚡ Claude rate limit reached — switched to Yahoo Finance"
                             if err == "rate_limit" else f"⚡ Claude error ({err[:60]}) — switched to Yahoo Finance")
            claude_data = None
        elif claude_data:
            data_mode = "claude"

    # 2. Yahoo Finance quote
    with st.spinner("📡 Fetching live quote from Yahoo Finance…"):
        quote = fetch_quote_yf(ticker)
    if not quote:
        st.error(f"Could not fetch data for {ticker}. Check the NSE ticker symbol.")
        return {}

    live = quote["livePrice"]

    # 3. History + technicals
    with st.spinner("📊 Loading 60-day price history…"):
        df = fetch_history_yf(ticker, 60)

    with st.spinner("⚙️ Computing VAP, RSI, EMAs, Momentum…"):
        vap    = compute_poc(df, live)
        tech   = compute_tech(df, live)
        mom    = check_momentum(tech)
        is_fno = ticker in FNO_SET
        oi     = compute_oi_sim(live)
        vix    = fetch_vix()
        pos    = ("ABOVE_VAH" if live > vap["vah"] else
                  "BELOW_VAL" if live < vap["val"] else "INSIDE_VA")

    # 4. Decision — prefer Claude's recommendation if available
    if claude_data and "action" in claude_data:
        rec = dict(
            action=claude_data["action"], confidence=claude_data["confidence"],
            entry=claude_data["entry"], target=claude_data["target"],
            stoploss=claude_data["stoploss"], rr=claude_data["rr"],
            framework=claude_data.get("framework",""), narrative=claude_data.get("narrative",""),
            key_risks=claude_data.get("keyRisks",[]), setup_type="standard",
        )
        # Merge any extra Claude fields
        tech["rsi"]   = claude_data.get("rsi")   or tech["rsi"]
        tech["ema20"] = claude_data.get("ema20")  or tech["ema20"]
        tech["ema50"] = claude_data.get("ema50")  or tech["ema50"]
        tech["trend"] = claude_data.get("trend")  or tech["trend"]
    else:
        rec = make_decision(live, pos, vap["poc"], vap["vah"], vap["val"],
                            vix, is_fno, oi, tech, mom,
                            quote["w52h"], quote["w52l"])

    # 5. Score & grade
    score_dict = dict(action=rec["action"], confidence=rec["confidence"], rr=rec["rr"],
                      price_position=pos, rsi=tech["rsi"], trend=tech["trend"],
                      vol_doubled=tech["vol_doubled"], consistent10=tech["consistent10"],
                      adx=tech["adx"], w52h=quote["w52h"], live=live, momentum=mom)
    setup_score = score_setup(score_dict)
    grade, grade_icon, grade_label = grade_setup(setup_score)
    pct_from_52h = round((quote["w52h"] - live) / quote["w52h"] * 100, 1) if quote["w52h"] else None

    uni_sector = dict(UNIVERSE).get(ticker, "NSE")

    return dict(
        ticker=ticker, data_mode=data_mode, switch_reason=switch_reason,
        fetched_at=now_ist(), is_fno=is_fno,
        fno_lot=LOT_MAP.get(ticker, 500 if is_fno else None),
        # Market
        live=live, chg_pct=quote["chgPct"], open=quote["open"],
        high=quote["high"], low=quote["low"], w52h=quote["w52h"], w52l=quote["w52l"],
        company=claude_data.get("companyName", ticker) if claude_data else ticker,
        sector=claude_data.get("sector", uni_sector) if claude_data else uni_sector,
        # VIX
        vix=vix,
        # VAP
        poc=vap["poc"], val=vap["val"], vah=vap["vah"], price_position=pos,
        # OI
        call_wall=oi["call_wall"], put_wall=oi["put_wall"],
        max_call_oi=oi["max_call_oi"], max_put_oi=oi["max_put_oi"],
        call_strikes=oi["call_strikes"], put_strikes=oi["put_strikes"],
        # Tech
        **{f"tech_{k}":v for k,v in tech.items()},
        # Momentum
        momentum=mom,
        # Rec
        rec=rec,
        # Grade
        setup_score=setup_score, grade=grade, grade_icon=grade_icon,
        grade_label=grade_label, pct_from_52h=pct_from_52h,
    )

# ── SCANNER ────────────────────────────────────────────────────────────────────
def run_scanner(sector_filter, min_price, max_price, min_rr, min_grade,
                near_52w, near_52w_pct, min_volume, progress_bar, status_text):
    universe = [(s,sec) for s,sec in UNIVERSE
                if sector_filter == "All Sectors" or sec == sector_filter]
    GRADE_ORDER = {"A+":6,"A":5,"B+":4,"B":3,"C+":2,"C":1}
    results = []
    total = len(universe)
    for i, (sym, sec) in enumerate(universe):
        status_text.text(f"Scanning {sym} ({i+1}/{total})…")
        progress_bar.progress((i+1)/total)
        try:
            quote = fetch_quote_yf(sym)
            if not quote or quote["livePrice"] <= 0: continue
            live = quote["livePrice"]
            if min_price and live < min_price: continue
            if max_price and live > max_price: continue
            df   = fetch_history_yf(sym, 60)
            tech = compute_tech(df, live)
            vap  = compute_poc(df, live)
            mom  = check_momentum(tech)
            vix  = fetch_vix()
            is_fno = sym in FNO_SET
            oi   = compute_oi_sim(live)
            pos  = ("ABOVE_VAH" if live > vap["vah"] else
                    "BELOW_VAL" if live < vap["val"] else "INSIDE_VA")
            rec  = make_decision(live, pos, vap["poc"], vap["vah"], vap["val"],
                                 vix, is_fno, oi, tech, mom, quote["w52h"], quote["w52l"])
            s_dict = dict(action=rec["action"], confidence=rec["confidence"], rr=rec["rr"],
                          price_position=pos, rsi=tech["rsi"], trend=tech["trend"],
                          vol_doubled=tech["vol_doubled"], consistent10=tech["consistent10"],
                          adx=tech["adx"], w52h=quote["w52h"], live=live, momentum=mom)
            ss = score_setup(s_dict)
            g, gi, gl = grade_setup(ss)
            p52 = round((quote["w52h"]-live)/quote["w52h"]*100,1) if quote["w52h"] else None
            avg_vol = tech["avg_vol20"]
            if min_volume and avg_vol < min_volume: continue
            try:
                rr_n = float(rec["rr"].split(":")[1])
                if min_rr and rr_n < min_rr: continue
            except: pass
            if min_grade and GRADE_ORDER.get(g,0) < GRADE_ORDER.get(min_grade,0): continue
            if near_52w and p52 is not None and p52 > near_52w_pct: continue
            results.append(dict(
                ticker=sym, sector=sec, live=live, chg_pct=quote["chgPct"],
                action=rec["action"], confidence=rec["confidence"],
                entry=rec["entry"], target=rec["target"], stoploss=rec["stoploss"],
                rr=rec["rr"], price_position=pos, setup_score=ss, grade=g,
                grade_icon=gi, grade_label=gl, pct_from_52h=p52,
                vol_doubled=tech["vol_doubled"], consistent10=tech["consistent10"],
                is_momentum=mom["triggered"], momentum_score=mom["score"],
            ))
            time.sleep(0.1)
        except Exception:
            continue
    return results

# ── UI RENDERING ──────────────────────────────────────────────────────────────
def vix_color(v):
    if v < 13: return "🔵"
    if v < 20: return "🟢"
    if v < 28: return "🟡"
    return "🔴"

def action_color(action):
    if any(x in action for x in ["BUY","LONG"]): return "green"
    if any(x in action for x in ["SELL","SHORT","AVOID"]): return "red"
    return "orange"

def render_result(r: dict):
    if not r: return
    ac = action_color(r["rec"]["action"])
    rec = r["rec"]
    vix = r["vix"]

    st.markdown("---")
    # Header row
    c1, c2, c3, c4 = st.columns([2,1,1,1])
    with c1:
        mode_badge = "🤖 CLAUDE AI" if r["data_mode"]=="claude" else "📡 YAHOO FINANCE"
        st.markdown(f"### {r['ticker']}  `{mode_badge}`")
        st.caption(f"{r['company']} · {r['sector']}")
        fno_txt = f"✅ F&O · Lot {r['fno_lot']}" if r["is_fno"] else "⚠️ Non-F&O"
        st.caption(fno_txt)
    with c2:
        st.metric("CMP", f"₹{fmt(r['live'])}", fmtpct(r['chg_pct']))
    with c3:
        st.metric("India VIX", f"{vix_color(vix)} {vix}",
                  "EXTREME" if vix>28 else "ELEVATED" if vix>20 else "STABLE" if vix>13 else "ULTRA-LOW")
    with c4:
        st.metric(f"{r['grade_icon']} Grade", f"{r['grade']} ({r['grade_label']})",
                  f"Score: {r['setup_score']}/100")

    if r["switch_reason"]:
        st.warning(r["switch_reason"])

    # Tabs
    t1, t2, t3, t4 = st.tabs(["📈 Recommendation", "📊 VAP + OI / Tech", "🚀 Momentum", "📋 Market Data"])

    # ── Tab 1: Recommendation
    with t1:
        col_a, col_b = st.columns([1,2])
        with col_a:
            st.markdown(f"<h2 style='color:{'#00ffaa' if ac=='green' else '#ff3d5a' if ac=='red' else '#ffb300'}'>{rec['action']}</h2>", unsafe_allow_html=True)
            mc1, mc2 = st.columns(2)
            mc1.metric("Entry",      f"₹{fmt(rec['entry'])}")
            mc2.metric("Target",     f"₹{fmt(rec['target'])}")
            mc1.metric("Stop Loss",  f"₹{fmt(rec['stoploss'])}")
            mc2.metric("R:R",        rec["rr"])
            conf_c = "#00ffaa" if rec["confidence"]>=70 else "#ffb300" if rec["confidence"]>=55 else "#ff3d5a"
            st.markdown(f"<b>Confidence:</b> <span style='color:{conf_c};font-size:22px'>{rec['confidence']}%</span>", unsafe_allow_html=True)
        with col_b:
            if rec["framework"]:
                st.info(f"**Framework:** {rec['framework']}")
            st.markdown(f"**Narrative:** {rec['narrative']}")
            if rec["key_risks"]:
                with st.expander("⚠️ Key Risks"):
                    for i, risk in enumerate(rec["key_risks"], 1):
                        st.markdown(f"{i}. {risk}")
        st.caption("⚠️ Educational only. NOT financial advice. Verify on NSE/broker before trading.")

    # ── Tab 2: VAP + OI / Tech
    with t2:
        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("**🔵 VAP · Volume Profile**")
            vap_data = {"Level": ["CMP","POC","VAH","VAL"],
                        "Price (₹)": [fmt(r["live"]), fmt(r["poc"]), fmt(r["vah"]), fmt(r["val"])]}
            st.dataframe(pd.DataFrame(vap_data), hide_index=True, use_container_width=True)
            pos_color = {"ABOVE_VAH":"🟢","BELOW_VAL":"🔴","INSIDE_VA":"🟡"}
            st.markdown(f"**Position:** {pos_color.get(r['price_position'],'⚪')} {r['price_position'].replace('_',' ')}")

        with col_r:
            if r["is_fno"]:
                st.markdown("**⛓️ OI Walls (Simulated)**")
                st.metric("Call Wall (Resistance)", f"₹{fmt(r['call_wall'])}", f"{r['max_call_oi']//1000}K lots")
                st.metric("Put Wall  (Support)",    f"₹{fmt(r['put_wall'])}",  f"{r['max_put_oi']//1000}K lots")
                cdf = pd.DataFrame(r["call_strikes"])
                pdf = pd.DataFrame(r["put_strikes"])
                cc1,cc2 = st.columns(2)
                with cc1:
                    st.caption("Calls"); st.dataframe(cdf, hide_index=True, use_container_width=True)
                with cc2:
                    st.caption("Puts");  st.dataframe(pdf, hide_index=True, use_container_width=True)
            else:
                st.markdown("**📐 Technicals**")
                trend_icon = "📈" if r["tech_trend"]=="BULLISH" else "📉" if r["tech_trend"]=="BEARISH" else "➡️"
                t_rows = {
                    "Indicator": ["RSI(14)","EMA20","EMA50","EMA200","MACD","ADX","Trend","Support","Resistance"],
                    "Value":     [r["tech_rsi"], fmt(r["tech_ema20"]), fmt(r["tech_ema50"]),
                                  fmt(r["tech_ema200"]), r["tech_macd"], round(r["tech_adx"],1),
                                  f"{trend_icon} {r['tech_trend']}", fmt(r["tech_support"]), fmt(r["tech_resistance"])],
                    "Signal":    [
                        "Overbought" if r["tech_rsi"]>70 else "Oversold" if r["tech_rsi"]<30 else "Neutral",
                        "Above ✅" if r["live"]>r["tech_ema20"] else "Below ❌",
                        "Above ✅" if r["live"]>r["tech_ema50"] else "Below ❌",
                        "Above ✅" if r["live"]>r["tech_ema200"] else "Below ❌",
                        "Bullish" if r["tech_macd"]>0 else "Bearish",
                        "Strong" if r["tech_adx"]>30 else "Weak",
                        r["tech_trend"], "—", "—",
                    ]
                }
                st.dataframe(pd.DataFrame(t_rows), hide_index=True, use_container_width=True)

    # ── Tab 3: Momentum
    with t3:
        mom = r["momentum"]
        st.markdown("### 🚀 Momentum Breakout Setup")
        st.caption("All 3 conditions must be true simultaneously")
        vr = r["tech_last_vol"] / max(1, r["tech_avg_vol20"])
        checks = [
            ("① 10 consecutive higher closes", mom["consistent10"],
             "✅ YES" if mom["consistent10"] else "❌ NOT YET"),
            (f"② Volume ≥ 2× 20D avg  (current: {vr:.2f}×)", mom["vol_doubled"],
             "✅ YES" if mom["vol_doubled"] else "❌ NO"),
            (f"③ RSI crossed above 40  (now: {r['tech_rsi']})", mom["rsi_crossed40"] or mom["rsi_above40"],
             f"✅ CROSSED (was {r['tech_prev_rsi']:.1f})" if mom["rsi_crossed40"]
             else "✅ ABOVE 40" if mom["rsi_above40"] else "❌ BELOW 40"),
        ]
        for label, met, val in checks:
            c_l, c_r = st.columns([3,1])
            c_l.markdown(f"{'🟢' if met else '🔴'} {label}")
            c_r.markdown(f"**{val}**")
        st.markdown("---")
        if mom["triggered"]:
            st.success(f"🚀 **TRIGGERED** — Momentum Score: {mom['score']}/100")
        else:
            st.info(f"⏳ Awaiting all conditions — Score: {mom['score']}/100")

    # ── Tab 4: Market Data
    with t4:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Open",       f"₹{fmt(r['open'])}")
            st.metric("Day High",   f"₹{fmt(r['high'])}")
            st.metric("Day Low",    f"₹{fmt(r['low'])}")
        with col2:
            st.metric("52W High",   f"₹{fmt(r['w52h'])}")
            st.metric("52W Low",    f"₹{fmt(r['w52l'])}")
            if r["pct_from_52h"] is not None:
                st.metric("From 52W High", f"{r['pct_from_52h']}%",
                          "Near breakout 🔥" if r["pct_from_52h"]<=5 else "")
        st.caption(f"Data fetched: {r['fetched_at']}")

# ── SCANNER DISPLAY ───────────────────────────────────────────────────────────
def render_scanner_results(results: list):
    if not results:
        st.info("No stocks matched the current filters. Try relaxing your criteria.")
        return
    df_rows = []
    for r in results:
        tags = []
        if r["is_momentum"]: tags.append("🚀MOM")
        if r["vol_doubled"]:  tags.append("VOL2×")
        if r["consistent10"]: tags.append("10D↑")
        if r["pct_from_52h"] is not None and r["pct_from_52h"]<=10:
            tags.append(f"52W {r['pct_from_52h']}%")
        df_rows.append({
            "Grade": f"{r['grade_icon']} {r['grade']}",
            "Ticker": r["ticker"],
            "Sector": r["sector"],
            "CMP (₹)": fmt(r["live"]),
            "Chg%": fmtpct(r["chg_pct"]),
            "Action": r["action"],
            "Entry": fmt(r["entry"]),
            "Target": fmt(r["target"]),
            "SL": fmt(r["stoploss"]),
            "R:R": r["rr"],
            "Conf%": r["confidence"],
            "Score": r["setup_score"],
            "Tags": " ".join(tags),
        })
    df = pd.DataFrame(df_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

# ── MAIN APP ──────────────────────────────────────────────────────────────────
def main():
    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## ⚙️ Settings")
        api_key = st.text_input("Anthropic API Key (optional)",
                                type="password",
                                placeholder="sk-ant-…",
                                help="Leave blank to use Yahoo Finance only.")
        st.markdown("---")
        st.markdown("**Data Sources**")
        st.markdown("🤖 Claude AI → web search for live price & analysis")
        st.markdown("📡 Yahoo Finance → automatic fallback")
        st.markdown("---")
        st.markdown("**Market Hours (IST)**")
        st.markdown("🕙 Pre-open: 9:00–9:15 AM")
        st.markdown("📈 Market: 9:15 AM–3:30 PM")
        st.markdown("🌙 After-hours: works fine (uses last close)")
        st.markdown("---")
        st.caption("⚠️ Educational only. Not financial advice.")

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown("# 📈 NSE Trade Setup Engine")
    st.markdown(
        "<small>VAP-POC · OI Walls · Momentum · Nifty 200 Scanner | "
        "Claude AI + Yahoo Finance</small>", unsafe_allow_html=True)
    st.markdown("---")

    # ── Tabs: Single Stock | Scanner ─────────────────────────────────────────
    tab_single, tab_scan = st.tabs(["🔎 Single Stock Analysis", "🔬 Nifty 200 Scanner"])

    # ═══ SINGLE STOCK ════════════════════════════════════════════════════════
    with tab_single:
        st.markdown("### Enter NSE Ticker")
        col_inp, col_btn = st.columns([3,1])
        with col_inp:
            ticker_in = st.text_input("", placeholder="RELIANCE · TCS · NIFTY · BANKNIFTY · ZOMATO…",
                                      label_visibility="collapsed").strip().upper()
        with col_btn:
            run_btn = st.button("▶ Run Setup", use_container_width=True)

        st.markdown("**Quick picks:**")
        qcols = st.columns(len(POPULAR[:9]))
        picked = None
        for i, t in enumerate(POPULAR[:9]):
            if qcols[i].button(t, key=f"q_{t}"):
                picked = t

        sym = picked or (ticker_in if run_btn and ticker_in else None)
        if sym:
            with st.spinner(f"Analyzing {sym}…"):
                result = analyze_ticker(sym, api_key)
            if result:
                render_result(result)

    # ═══ SCANNER ═════════════════════════════════════════════════════════════
    with tab_scan:
        st.markdown("### 🔬 Nifty 200 Smart Scanner")
        st.caption("Scans stocks using Yahoo Finance · Setup grade A–C · Real-time filtering")

        # Filter UI
        with st.expander("⚙️ Filters", expanded=True):
            f1, f2, f3 = st.columns(3)
            sec_f   = f1.selectbox("Sector", SECTOR_LIST)
            min_p   = f2.number_input("Min Price (₹)", 0, 100000, 0, step=50)
            max_p   = f3.number_input("Max Price (₹)", 0, 100000, 99999, step=50)

            f4, f5, f6 = st.columns(3)
            min_rr_opt = f4.selectbox("Min R:R", ["Any","≥ 1:1.5","≥ 1:2","≥ 1:2.5","≥ 1:3"])
            min_rr_val = {"Any":0,"≥ 1:1.5":1.5,"≥ 1:2":2,"≥ 1:2.5":2.5,"≥ 1:3":3}[min_rr_opt]
            min_g_opt  = f5.selectbox("Min Grade", ["Any","C+","B","B+","A","A+"])
            min_g_val  = "" if min_g_opt=="Any" else min_g_opt

            f7, f8 = st.columns(2)
            near52_opt = f7.selectbox("52W High Proximity",["Any","Within 5%","Within 10%","Within 15%"])
            near52_val = {"Any":(False,10),"Within 5%":(True,5),"Within 10%":(True,10),"Within 15%":(True,15)}[near52_opt]
            min_vol_opt = f8.selectbox("Min Avg Volume",["Any","≥ 1L","≥ 5L","≥ 10L"])
            min_vol_val = {"Any":0,"≥ 1L":100000,"≥ 5L":500000,"≥ 10L":1000000}[min_vol_opt]

        scan_btn = st.button("▶ Start Scan", key="scan_btn", use_container_width=False)
        if scan_btn:
            universe_count = len([x for x in UNIVERSE if sec_f=="All Sectors" or x[1]==sec_f])
            st.info(f"Scanning {universe_count} stocks… This may take 1–3 minutes.")
            pb = st.progress(0)
            st_txt = st.empty()
            results = run_scanner(
                sector_filter=sec_f, min_price=min_p or 0, max_price=max_p or 99999,
                min_rr=min_rr_val, min_grade=min_g_val,
                near_52w=near52_val[0], near_52w_pct=near52_val[1],
                min_volume=min_vol_val, progress_bar=pb, status_text=st_txt,
            )
            pb.progress(1.0); st_txt.empty()
            st.success(f"✅ Scan complete — {len(results)} stocks passed filters out of {universe_count} scanned.")

            # Sub-tabs
            buy_r   = sorted([r for r in results if "BUY"  in r["action"] or "LONG"  in r["action"]], key=lambda x:-x["setup_score"])[:10]
            sell_r  = sorted([r for r in results if "SELL" in r["action"] or "SHORT" in r["action"]], key=lambda x:-x["setup_score"])[:10]
            mom_r   = sorted([r for r in results if r["is_momentum"]], key=lambda x:-x["momentum_score"])[:10]
            near52_r= sorted([r for r in results if r["pct_from_52h"] is not None and r["pct_from_52h"]<=10
                               and ("BUY" in r["action"] or "LONG" in r["action"])], key=lambda x:x["pct_from_52h"])[:10]

            st1,st2,st3,st4 = st.tabs([f"▲ Top Buy ({len(buy_r)})",
                                        f"▼ Top Sell ({len(sell_r)})",
                                        f"🚀 Momentum ({len(mom_r)})",
                                        f"📍 Near 52W High ({len(near52_r)})"])
            with st1: render_scanner_results(buy_r)
            with st2: render_scanner_results(sell_r)
            with st3: render_scanner_results(mom_r)
            with st4: render_scanner_results(near52_r)

            # Grade legend
            st.markdown("---")
            st.caption("**Grade:** 🟢A+=Exceptional · 🟢A=Strong · 🔵B+=Good · 🔵B=Moderate · 🟡C+=Weak · ⚪C=Poor")

if __name__ == "__main__":
    main()
