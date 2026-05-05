import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from datetime import datetime
import pytz
import warnings
import koreanize_matplotlib
warnings.filterwarnings("ignore")

st.set_page_config(page_title="AInvest", page_icon="", layout="wide")

st.markdown("""
<style>
.main,.stApp{background-color:#0e1117;}
.metric-card{
    background:linear-gradient(135deg,#1e2530,#16202c);
    border:1px solid #2d3748;border-radius:12px;
    padding:16px;text-align:center;margin:4px;
}
.section-title{
    font-size:1.1rem;font-weight:700;color:#e2e8f0;
    border-left:4px solid #00d4aa;padding-left:10px;margin:16px 0 10px 0;
}
.top-input-box{
    background:#1e2530;border:1px solid #2d3748;
    border-radius:14px;padding:24px 32px;margin-bottom:24px;
}
</style>
""", unsafe_allow_html=True)

TICKER_MAP = {
    "엔비디아":"NVDA","nvidia":"NVDA","nvda":"NVDA",
    "테슬라":"TSLA","tesla":"TSLA","tsla":"TSLA",
    "애플":"AAPL","apple":"AAPL","aapl":"AAPL",
    "마이크로소프트":"MSFT","microsoft":"MSFT","msft":"MSFT",
    "구글":"GOOGL","google":"GOOGL","googl":"GOOGL","알파벳":"GOOGL",
    "아마존":"AMZN","amazon":"AMZN","amzn":"AMZN",
    "메타":"META","meta":"META",
    "팔란티어":"PLTR","palantir":"PLTR","pltr":"PLTR",
    "아이온큐":"IONQ","ionq":"IONQ",
    "코인베이스":"COIN","coinbase":"COIN","coin":"COIN",
    "삼성전자":"005930.KS","sk하이닉스":"000660.KS",
    "카카오":"035720.KS","네이버":"035420.KS",
}

def resolve_ticker(query):
    return TICKER_MAP.get(query.strip().lower(), query.strip().upper())

def get_market_status(ticker):
    is_korean = ticker.endswith(".KS") or ticker.endswith(".KQ")
    if is_korean:
        now = datetime.now(pytz.timezone("Asia/Seoul"))
        t, wk = now.time(), now.weekday()
        from datetime import time as dtime
        if wk >= 5:
            return {"status":"휴장","color":"#718096"}
        if dtime(9,0) <= t <= dtime(15,30):
            return {"status":"정규장","color":"#00d4aa"}
        return {"status":"장 마감","color":"#718096"}
    now = datetime.now(pytz.timezone("America/New_York"))
    t, wk = now.time(), now.weekday()
    from datetime import time as dtime
    if wk >= 5:
        return {"status":"휴장 (주말)","color":"#718096"}
    if dtime(4,0) <= t < dtime(9,30):
        return {"status":"프리마켓","color":"#f6c90e"}
    if dtime(9,30) <= t < dtime(16,0):
        return {"status":"정규장","color":"#00d4aa"}
    if dtime(16,0) <= t < dtime(20,0):
        return {"status":"애프터마켓","color":"#a78bfa"}
    return {"status":"장 마감","color":"#718096"}

def calc_rsi(close, length=14):
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=length-1, min_periods=length).mean()
    avg_loss = loss.ewm(com=length-1, min_periods=length).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    return 100 - (100 / (1 + rs))

def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast    = close.ewm(span=fast, adjust=False).mean()
    ema_slow    = close.ewm(span=slow, adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram   = macd_line - signal_line
    return macd_line, signal_line, histogram

def calc_bbands(close, length=20):
    mid   = close.rolling(length).mean()
    std   = close.rolling(length).std()
    return mid + 2*std, mid, mid - 2*std

def calc_atr(high, low, close, length=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(com=length-1, min_periods=length).mean()

def calc_indicators(df):
    df = df.copy()
    df["RSI"]                              = calc_rsi(df["Close"])
    df["MACD"], df["MACD_signal"], df["MACD_hist"] = calc_macd(df["Close"])
    df["BB_upper"], df["BB_mid"], df["BB_lower"]   = calc_bbands(df["Close"])
    df["ATR"]  = calc_atr(df["High"], df["Low"], df["Close"])
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    return df

@st.cache_data(ttl=300)
def fetch_stock_data(ticker):
    stk  = yf.Ticker(ticker)
    info = stk.info
    df_d = stk.history(period="3mo",  interval="1d")
    df_w = stk.history(period="6mo",  interval="1wk")
    df_m = stk.history(period="24mo", interval="1mo")
    return info, df_d, df_w, df_m

def calc_trend_score(df):
    """0~100 추세 점수 계산"""
    df = calc_indicators(df.copy()).dropna()
    if len(df) < 5:
        return 50
    close  = float(df["Close"].iloc[-1])
    rsi    = float(df["RSI"].iloc[-1])
    macd_h = float(df["MACD_hist"].iloc[-1])
    macd_v = float(df["MACD"].iloc[-1])
    bb_up  = float(df["BB_upper"].iloc[-1])
    bb_lo  = float(df["BB_lower"].iloc[-1])
    ma20   = float(df["MA20"].iloc[-1])
    ma50   = float(df["MA50"].iloc[-1]) if df["MA50"].notna().any() else close

    score = 0
    if rsi < 30:     score += 30
    elif rsi < 45:   score += 15
    elif rsi > 70:   score -= 30
    elif rsi > 55:   score -= 10

    if macd_h > 0 and macd_v > 0:   score += 25
    elif macd_h > 0:                  score += 10
    elif macd_h < 0 and macd_v < 0: score -= 25
    elif macd_h < 0:                  score -= 10

    bb_range = bb_up - bb_lo + 1e-9
    bb_pos   = (close - bb_lo) / bb_range
    if bb_pos < 0.2:    score += 20
    elif bb_pos > 0.85: score -= 20

    if close > ma20 > ma50:   score += 15
    elif close < ma20 < ma50: score -= 15

    # -100~100 -> 0~100
    return int((max(-100, min(100, score)) + 100) / 2)

def ai_analyze(df_d, seed):
    df = calc_indicators(df_d.copy()).dropna()
    if len(df) < 5:
        return None

    close  = float(df["Close"].iloc[-1])
    prev   = float(df["Close"].iloc[-2])
    change = (close - prev) / prev * 100

    rsi    = float(df["RSI"].iloc[-1])
    macd_h = float(df["MACD_hist"].iloc[-1])
    macd_v = float(df["MACD"].iloc[-1])
    bb_up  = float(df["BB_upper"].iloc[-1])
    bb_lo  = float(df["BB_lower"].iloc[-1])
    atr    = float(df["ATR"].iloc[-1])
    ma20   = float(df["MA20"].iloc[-1])
    ma50   = float(df["MA50"].iloc[-1]) if df["MA50"].notna().any() else close

    high52    = float(df["High"].tail(252).max())
    low52     = float(df["Low"].tail(252).min())
    pos52     = (close - low52) / (high52 - low52 + 1e-9) * 100
    vol_avg   = df["Volume"].tail(20).mean()
    vol_ratio = float(df["Volume"].iloc[-1]) / vol_avg if vol_avg > 0 else 1.0

    score = 0
    if rsi < 30:     score += 30
    elif rsi < 45:   score += 15
    elif rsi > 70:   score -= 30
    elif rsi > 55:   score -= 10

    if macd_h > 0 and macd_v > 0:   score += 25
    elif macd_h > 0:                  score += 10
    elif macd_h < 0 and macd_v < 0: score -= 25
    elif macd_h < 0:                  score -= 10

    bb_range = bb_up - bb_lo + 1e-9
    bb_pos   = (close - bb_lo) / bb_range
    if bb_pos < 0.2:    score += 20
    elif bb_pos > 0.85: score -= 20

    if close > ma20 > ma50:   score += 15
    elif close < ma20 < ma50: score -= 15

    if vol_ratio > 1.5: score += 5 if score > 0 else -5
    score = max(-100, min(100, score))

    if score >= 55:    rec = ("적극 매수", 5, "#00d4aa")
    elif score >= 20:  rec = ("매수 추천", 4, "#68d391")
    elif score >= -20: rec = ("보류",      3, "#f6c90e")
    elif score >= -55: rec = ("매도 추천", 2, "#f6ad55")
    else:              rec = ("적극 매도", 1, "#ff4b4b")

    buy_price  = round(close * 0.995, 2)
    target1    = round(close + atr * 2.5, 2)
    stop_loss  = round(close - atr * 1.5, 2)
    exp_return = (target1 - buy_price) / buy_price * 100
    quantity   = int(seed // close) if close > 0 else 0
    exp_profit = round((target1 - buy_price) * quantity, 2)

    risk_factors = {
        "변동성 (ATR)":     min(100, int((atr / close) * 1000)),
        "52주 고점 근접도": int(pos52),
        "RSI 과매수":       min(100, max(0, int((rsi - 50) * 1.5))),
        "거래량 급변":      min(100, max(0, int((vol_ratio - 1) * 50))),
        "추세 역행 위험":   70 if close < ma50 else 30,
    }
    total_risk = int(np.mean(list(risk_factors.values())))
    if total_risk >= 70:   risk_grade = ("높음", "#ff4b4b")
    elif total_risk >= 40: risk_grade = ("중간", "#f6c90e")
    else:                  risk_grade = ("낮음", "#00d4aa")

    if score >= 40:
        trend_text   = "강세 추세 — 기술적 지표 다수 매수 신호"
        trend_detail = f"RSI {rsi:.1f}, MACD 양전환, 볼린저 하단 지지"
    elif score >= 10:
        trend_text   = "약세 회복 — 단기 반등 신호 감지"
        trend_detail = f"RSI {rsi:.1f}, 단기 이평선 상향 돌파"
    elif score >= -10:
        trend_text   = "횡보 구간 — 방향성 불분명"
        trend_detail = f"RSI {rsi:.1f}, 볼린저 중간밴드 근처 등락"
    elif score >= -40:
        trend_text   = "약세 추세 — 단기 하락 압력"
        trend_detail = f"RSI {rsi:.1f}, MACD 음전환 확인"
    else:
        trend_text   = "강한 하락세 — 전 지표 약세"
        trend_detail = f"RSI {rsi:.1f}, 이평선 데드크로스"

    return dict(
        close=close, prev=prev, change=change,
        rsi=rsi, macd_h=macd_h, bb_pos=bb_pos,
        ma20=ma20, ma50=ma50, score=score, rec=rec,
        buy_price=buy_price, target1=target1,
        stop_loss=stop_loss, exp_return=exp_return,
        quantity=quantity, exp_profit=exp_profit,
        risk_total=total_risk, risk_grade=risk_grade,
        risk_factors=risk_factors,
        trend_text=trend_text, trend_detail=trend_detail,
        high52=high52, low52=low52, vol_ratio=vol_ratio, atr=atr,
    )

# ── 원형 추세 게이지 ──────────────────────────────────────────────
def plot_circle_trend(score_d, score_w, score_m):
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.2), facecolor="#1e2530")
    labels  = ["일봉 (3개월)", "주봉 (6개월)", "월봉 (2년)"]
    scores  = [score_d, score_w, score_m]

    for ax, label, score in zip(axes, labels, scores):
        ax.set_facecolor("#1e2530")
        ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.3, 1.3)
        ax.set_aspect("equal"); ax.axis("off")

        # 색상 결정
        if score >= 65:    col = "#00d4aa"
        elif score >= 50:  col = "#68d391"
        elif score >= 40:  col = "#f6c90e"
        elif score >= 25:  col = "#f6ad55"
        else:              col = "#ff4b4b"

        # 배경 원
        bg = plt.Circle((0,0), 1.0, color="#2d3748", zorder=1)
        ax.add_patch(bg)

        # 진행 호 (0~100 -> 0~360도, -90도 시작)
        angle = score / 100 * 360
        theta = np.linspace(np.radians(90), np.radians(90 - angle), 300)
        ax.fill_between(
            np.concatenate([[0], np.cos(theta)]),
            np.concatenate([[0], np.sin(theta)]),
            color=col, alpha=0.15, zorder=2
        )
        ax.plot(np.cos(theta), np.sin(theta), color=col, lw=5, zorder=3)

        # 내부 흰 원 (도넛 효과)
        inner = plt.Circle((0,0), 0.65, color="#1e2530", zorder=4)
        ax.add_patch(inner)

        # 점수 텍스트
        ax.text(0, 0.12, str(score), ha="center", va="center",
                fontsize=26, fontweight="bold", color=col, zorder=5)
        ax.text(0, -0.22, "/ 100", ha="center", va="center",
                fontsize=10, color="#718096", zorder=5)

        # 레이블
        ax.text(0, -1.22, label, ha="center", va="top",
                fontsize=10, color="#a0aec0")

    plt.tight_layout(pad=1.5)
    return fig

# ── 매매 추천 게이지 ──────────────────────────────────────────────
def plot_rec_gauge(score, rec):
    fig, ax = plt.subplots(figsize=(10, 1.6), facecolor="#1e2530")
    ax.set_facecolor("#1e2530"); ax.set_xlim(0,5); ax.set_ylim(0,1); ax.axis("off")

    labels  = ["적극 매도", "매도 추천", "보류", "매수 추천", "적극 매수"]
    colors_on  = ["#ff4b4b", "#f6ad55", "#f6c90e", "#68d391", "#00d4aa"]
    active_idx = rec[1] - 1  # rec[1] = 1~5

    for i, (label, col) in enumerate(zip(labels, colors_on)):
        is_active = (i == active_idx)
        bar_col   = col       if is_active else "#2d3748"
        txt_col   = col       if is_active else "#4a5568"
        border    = col       if is_active else "#2d3748"
        lw        = 2.5       if is_active else 1.0

        rect = mpatches.FancyBboxPatch(
            (i + 0.06, 0.22), 0.88, 0.56,
            boxstyle="round,pad=0.04",
            linewidth=lw, edgecolor=border,
            facecolor=bar_col if is_active else "#1a2233",
            zorder=2
        )
        ax.add_patch(rect)

        ax.text(i + 0.5, 0.5, label,
                ha="center", va="center", fontsize=10.5,
                fontweight="bold" if is_active else "normal",
                color=txt_col, zorder=3)

    plt.tight_layout(pad=0.3)
    return fig

# ── 리스크 바 ─────────────────────────────────────────────────────
def plot_risk(risk_factors, total_risk, risk_grade):
    fig, ax = plt.subplots(figsize=(8, 3), facecolor="#1e2530")
    ax.set_facecolor("#1e2530"); ax.axis("off")
    items = list(risk_factors.items())
    ys    = np.linspace(0.85, 0.1, len(items))
    for (factor, val), y in zip(items, ys):
        col = "#00d4aa" if val < 40 else ("#f6c90e" if val < 70 else "#ff4b4b")
        ax.text(0.0, y, factor, ha="left", va="center", fontsize=9,
                color="#e2e8f0", transform=ax.transAxes)
        ax.barh(y, 1.0,     left=0.38, height=0.1,
                color="#2d3748", alpha=0.4, transform=ax.transAxes)
        ax.barh(y, val/100, left=0.38, height=0.1,
                color=col, alpha=0.9, transform=ax.transAxes)
        ax.text(0.98, y, str(val), ha="right", va="center", fontsize=8.5,
                color=col, transform=ax.transAxes)
    ax.text(0.0, 0.0,
            f"종합 리스크 점수: {total_risk}  [{risk_grade[0]}]",
            ha="left", va="bottom", fontsize=10, fontweight="bold",
            color=risk_grade[1], transform=ax.transAxes)
    plt.tight_layout()
    return fig

def mcard(label, val, sub, color):
    return f"""<div class="metric-card">
        <div style="color:#8892a4;font-size:.8rem;">{label}</div>
        <div style="color:{color};font-size:1.5rem;font-weight:700;">{val}</div>
        <div style="color:{color};font-size:.8rem;">{sub}</div></div>"""

# ═══════════════════════════════════════════════════════════════════
#  메인 레이아웃
# ═══════════════════════════════════════════════════════════════════
st.markdown("# AInvest ")

# ── 상단 입력 영역 (본문 통합) ────────────────────────────────────
with st.container():
    st.markdown('<div class="top-input-box">', unsafe_allow_html=True)
    col_seed, col_query, col_btn = st.columns([2, 3, 1.2])
    with col_seed:
        st.markdown("**매수 시드 (USD / KRW)**")
        seed = st.number_input("seed", min_value=100.0, value=10000.0,
                               step=100.0, format="%.0f", label_visibility="collapsed")
    with col_query:
        st.markdown("**종목 검색**")
        query = st.text_input("query", placeholder="엔비디아, TSLA, 삼성전자 ...",
                              label_visibility="collapsed")
    with col_btn:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        analyze_btn = st.button("지금 분석하기", use_container_width=True, type="primary")
    st.markdown('</div>', unsafe_allow_html=True)

if not analyze_btn or not query:
    st.markdown("""<div style="text-align:center;padding:80px 0;color:#4a5568;">
        <div style="font-size:3rem;">[ AInvest ]</div>
        <div style="font-size:1.1rem;margin-top:16px;line-height:2;">
            종목명 또는 티커를 입력하고<br>
            <b>지금 분석하기</b> 버튼을 눌러주세요.
        </div></div>""", unsafe_allow_html=True)
    st.stop()

ticker = resolve_ticker(query)

with st.spinner(f"{ticker} 분석 중 ..."):
    try:
        info, df_d, df_w, df_m = fetch_stock_data(ticker)
        result = ai_analyze(df_d, seed)
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        st.stop()

if result is None:
    st.error("데이터 부족으로 분석할 수 없습니다.")
    st.stop()

name     = info.get("longName", ticker)
currency = info.get("currency", "USD")
ms       = get_market_status(ticker)
close    = result["close"]
change   = result["change"]

# ── 종목 헤더 ─────────────────────────────────────────────────────
h1, h2 = st.columns([4, 1])
with h1:
    st.markdown(f"### {name}  `{ticker}`")
with h2:
    st.markdown(f"""<div style="text-align:right;margin-top:12px;">
        <span style="background:{ms['color']}22;color:{ms['color']};
        border:1px solid {ms['color']}66;padding:5px 16px;
        border-radius:20px;font-size:.9rem;font-weight:600;">
        {ms['status']}</span></div>""", unsafe_allow_html=True)

# ── 핵심 지표 카드 ────────────────────────────────────────────────
price_color = "#00d4aa" if change >= 0 else "#ff4b4b"
arrow = "▲" if change >= 0 else "▼"
rsi   = result["rsi"]
rsi_c = "#ff4b4b" if rsi>70 else ("#00d4aa" if rsi<30 else "#f6c90e")
rsi_label = "과매수" if rsi>70 else ("과매도" if rsi<30 else "중립")
vr    = result["vol_ratio"]
vr_c  = "#f6c90e" if vr>1.5 else "#8892a4"
vr_label  = "급등" if vr>2 else ("증가" if vr>1.2 else "보통")

c1,c2,c3,c4,c5 = st.columns(5)
with c1: st.markdown(mcard("현재가",    f"{close:,.2f}",           f"{arrow} {abs(change):.2f}%",      price_color), unsafe_allow_html=True)
with c2: st.markdown(mcard("전일 종가", f"{result['prev']:,.2f}",  currency,                           "#e2e8f0"),   unsafe_allow_html=True)
with c3: st.markdown(mcard("RSI (14)", f"{rsi:.1f}",              rsi_label,                          rsi_c),       unsafe_allow_html=True)
with c4: st.markdown(mcard("52주 고점",f"{result['high52']:,.1f}",f"저: {result['low52']:,.1f}",      "#e2e8f0"),   unsafe_allow_html=True)
with c5: st.markdown(mcard("거래량 비율",f"{vr:.2f}x",            vr_label,                           vr_c),        unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 시장 추세 ─────────────────────────────────────────────────────
st.markdown('<div class="section-title">시장 추세</div>', unsafe_allow_html=True)
t1, t2 = st.columns([3, 1])
with t1:
    st.markdown(f"""<div style="background:#1e2530;border:1px solid #2d3748;
        border-radius:10px;padding:14px 20px;">
        <div style="font-size:1.05rem;color:#e2e8f0;font-weight:600;">{result['trend_text']}</div>
        <div style="font-size:.85rem;color:#8892a4;margin-top:6px;">{result['trend_detail']}</div>
    </div>""", unsafe_allow_html=True)
with t2:
    sc   = result["score"]
    sc_c = "#00d4aa" if sc>20 else ("#ff4b4b" if sc<-20 else "#f6c90e")
    st.markdown(mcard("AI 종합 점수", f"{sc:+d}", "-100 ~ +100", sc_c), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 주식 분석 — 원형 추세 지수 ───────────────────────────────────
st.markdown('<div class="section-title">주식 분석 — 추세 지수</div>', unsafe_allow_html=True)

score_d = calc_trend_score(df_d)
score_w = calc_trend_score(df_w)
score_m = calc_trend_score(df_m)

fig_circle = plot_circle_trend(score_d, score_w, score_m)
st.pyplot(fig_circle); plt.close()

st.markdown("<br>", unsafe_allow_html=True)

# ── AI 매매 추천 ──────────────────────────────────────────────────
st.markdown('<div class="section-title">AI 매매 추천</div>', unsafe_allow_html=True)
fig_rec = plot_rec_gauge(result["score"], result["rec"])
st.pyplot(fig_rec); plt.close()

st.markdown("<br>", unsafe_allow_html=True)

# ── 매매 전략 ─────────────────────────────────────────────────────
st.markdown('<div class="section-title">매매 전략</div>', unsafe_allow_html=True)
b1,b2,b3,b4,b5 = st.columns(5)
er   = result["exp_return"]
er_c = "#00d4aa" if er>0 else "#ff4b4b"
with b1: st.markdown(mcard("매수가",      f"{result['buy_price']:,.2f}", currency, "#68d391"), unsafe_allow_html=True)
with b2: st.markdown(mcard("1차 목표가",  f"{result['target1']:,.2f}",  currency, "#00d4aa"), unsafe_allow_html=True)
with b3: st.markdown(mcard("손절가",      f"{result['stop_loss']:,.2f}", currency, "#ff4b4b"), unsafe_allow_html=True)
with b4: st.markdown(mcard("추천 수량",   f"{result['quantity']:,} 주",  "",        "#a78bfa"), unsafe_allow_html=True)
with b5: st.markdown(mcard("예상 수익률", f"{er:+.2f}%",                 "",        er_c),     unsafe_allow_html=True)

ep   = result["exp_profit"]
ep_c = "#00d4aa" if ep>0 else "#ff4b4b"
st.markdown(f"""<div style="background:#1e2530;border:1px solid #2d3748;
    border-radius:10px;padding:12px 20px;margin-top:10px;">
    시드 <b>{seed:,.0f} {currency}</b> 기준 &nbsp;|&nbsp;
    수량 <b>{result['quantity']}주</b> 매수 시 예상 수익금:
    <span style="color:{ep_c};font-weight:700;">{ep:+,.2f} {currency}</span>
    (목표가 도달 시)
</div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── 리스크 스코어 ─────────────────────────────────────────────────
st.markdown('<div class="section-title">리스크 스코어</div>', unsafe_allow_html=True)
fig_risk = plot_risk(result["risk_factors"], result["risk_total"], result["risk_grade"])
st.pyplot(fig_risk); plt.close()

st.markdown("---")
st.markdown("""<div style="font-size:.72rem;color:#4a5568;text-align:center;">
AInvest는 AI 기술적 분석 보조 도구입니다. 본 결과는 투자 권유가 아니며
모든 투자 결정의 책임은 투자자 본인에게 있습니다. 2026 AInvest
</div>""", unsafe_allow_html=True)
