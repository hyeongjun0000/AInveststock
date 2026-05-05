import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
<<<<<<< HEAD
from datetime import datetime, date
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="AInvest", page_icon="📈",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
html, body, .stApp { background-color:#0d0d1a !important; color:white;
    font-family:'Noto Sans KR',sans-serif; }
.block-container { padding:1.2rem 1.5rem; max-width:860px; margin:auto; }
.stButton > button {
    background:linear-gradient(135deg,#e05a00,#c94400) !important;
    color:white !important; border:none !important; border-radius:16px !important;
    font-size:18px !important; font-weight:900 !important;
    padding:18px 0 !important; width:100% !important; letter-spacing:1px; margin-top:8px;
}
.stButton > button:hover { opacity:0.9; }
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background:#1a1a2e !important; color:white !important;
    border:1px solid #2a2a40 !important; border-radius:12px !important;
    font-size:15px !important; padding:10px 14px !important;
}
.stTextInput label, .stNumberInput label { color:#888 !important; font-size:12px !important; }
.card { background:#161626; border-radius:14px; padding:18px 20px; margin-bottom:10px; }
.lbl  { font-size:12px; color:#888; margin-bottom:6px; }
.sub  { font-size:12px; color:#666; margin-top:5px; }
.divider { height:1px; background:#1e1e30; margin:14px 0; }
.section-title { font-size:13px; font-weight:700; color:#555;
    letter-spacing:2px; text-transform:uppercase; margin:18px 0 8px; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ──────────────────────────────────────────────────────────────────
def calc_stoch(df, k=14, d=3):
    lo  = df["Low"].rolling(k).min()
    hi  = df["High"].rolling(k).max()
    pk  = 100 * (df["Close"] - lo) / (hi - lo + 1e-9)
    pd_ = pk.rolling(d).mean()
    return round(float(pk.iloc[-1]), 1), round(float(pd_.iloc[-1]), 1)

def stoch_html(label, k, d):
    clr = "#e84040" if k >= d else "#4a9eff"
    arrow = "↑" if k >= d else "↓"
    pos = max(2, min(97, k))
    return f"""<div class="card">
      <div class="lbl">{label}</div>
      <div style="font-size:28px;font-weight:900;color:{clr};margin-bottom:10px;">{arrow} {k}</div>
      <div style="position:relative;height:10px;border-radius:6px;
           background:linear-gradient(to right,#1e3a7a 0%,#1e3a7a 25%,#2a2a40 25%,#2a2a40 75%,#5a1a1a 75%);">
        <div style="position:absolute;left:{pos}%;top:50%;transform:translate(-50%,-50%);
             width:16px;height:16px;border-radius:50%;background:{clr};box-shadow:0 0 6px {clr};"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:11px;color:#555;margin-top:4px;">
        <span>20</span><span>80</span>
      </div>
      <div style="font-size:11px;color:#555;margin-top:4px;">%K {k} · %D {d}</div>
    </div>"""

def pct_bar_html(label, icon, price, pct, desc, positive=True):
    bar_bg = "#4a1a1a" if positive else "#1a2050"
    txt_c  = "#e84040" if positive else "#4a9eff"
    return f"""<div class="card">
      <div class="lbl">{icon} {label}</div>
      <div style="font-size:26px;font-weight:900;color:white;margin-bottom:6px;">${price:,.2f}</div>
      <div style="background:{bar_bg};border-radius:5px;padding:4px 12px;display:inline-block;margin-bottom:8px;">
        <span style="color:{txt_c};font-weight:700;font-size:13px;">{pct:+.1f}%</span>
      </div>
      <div class="sub">{desc}</div>
    </div>"""

@st.cache_data(ttl=300)
def get_hist(ticker, period, interval):
    df = yf.Ticker(ticker).history(period=period, interval=interval)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    return df.dropna(subset=["Close"])

@st.cache_data(ttl=600)
def get_fx():
    try:
        return float(yf.Ticker("USDKRW=X").fast_info["lastPrice"])
    except:
        return 1380.0

def ai_levels(df, price):
    c, h, l = df["Close"].dropna(), df["High"].dropna(), df["Low"].dropna()
    atr   = pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1).tail(14).mean()
    ma20  = c.tail(20).mean()
    hi52  = h.tail(252).max()
    lo252 = l.tail(252).min()
    return dict(
        buy   = round(price * 1.003, 2),
        sell  = round(price + float(atr) * 2.0, 2),
        mid_t = round(max(float(h.tail(60).max()), price * 1.25), 2),
        lng_t = round(max(float(hi52), price * 1.60), 2),
        mid_d = round(min(float(l.tail(20).min()), float(ma20) * 0.95), 2),
        lng_d = round(float(lo252) * 1.05, 2),
        hi52  = float(hi52), atr = float(atr)
    )

def risk_score(stoch_wk, vol_ratio, above_ma, sell_ratio):
    s, f = 0, {}
    if   stoch_wk >= 80: f["크게 오른 구간 (과열)"] = 20; s += 20
    elif stoch_wk >= 60: f["주봉 K 중상단"]          = 9;  s += 9
    else:                f["크게 눌린 구간"]          = 0
    if   vol_ratio > 1.5: f["거래량 급증"]            = 10; s += 10
    elif vol_ratio > 1.2: f["거래량 소폭 증가"]       = 5;  s += 5
    if not above_ma:      f["단기 이평 하방"]          = 10; s += 10
    else:                 f["단기 급등 구간"]          = 15; s += 15
    if sell_ratio > 0.3:  f["애널리스트 부정적"]       = 10; s += 10
    return min(s, 100), f

# ── 스윙 신호 계산 ────────────────────────────────────────────────────────────
SIGNAL_META = {
    "strong_short": ("⚡ STRONG SHORT", "#8b00ff", "인버스 ETF 매수 · 풋옵션 고려"),
    "short":        ("🔻 SHORT",        "#4a9eff", "인버스 ETF 분할 매수 고려"),
    "hodl":         ("⏸ HODL",          "#888888", "현금 보유 또는 소량 포지션 유지"),
    "long":         ("🔺 LONG",         "#ff9500", "분할 매수 진입 고려"),
    "strong_long":  ("🚀 STRONG LONG",  "#e84040", "콜옵션 · 적극 매수 진입 고려"),
}
STEP_ORDER = ["strong_short", "short", "hodl", "long", "strong_long"]

def swing_signal(stoch_wk_k, stoch_wk_d, stoch_mk_k, stoch_mk_d,
                 qqq_wk_k, wk_ret, mo_ret, above_ma,
                 vol_ratio, from_hi, buy_ratio, sell_ratio):
    sigs = {}
    # 주봉 스토캐스틱
    if   stoch_wk_k < 20 and stoch_wk_k > stoch_wk_d: sigs["주봉 스토 과매도 반등"] = +22
    elif stoch_wk_k < 20:                               sigs["주봉 스토 과매도"]     = +15
    elif stoch_wk_k > 80 and stoch_wk_k < stoch_wk_d: sigs["주봉 스토 과매수 꺾임"] = -22
    elif stoch_wk_k > 80:                               sigs["주봉 스토 과매수"]     = -15
    elif stoch_wk_k > stoch_wk_d:                       sigs["주봉 스토 상향교차"]   = +10
    else:                                                sigs["주봉 스토 하향교차"]   = -10
    # 월봉 스토캐스틱
    if   stoch_mk_k < 25:                sigs["월봉 스토 과매도"]     = +15
    elif stoch_mk_k > 75:                sigs["월봉 스토 과매수"]     = -15
    elif stoch_mk_k > stoch_mk_d:        sigs["월봉 스토 상승 추세"]  = +8
    else:                                sigs["월봉 스토 하락 추세"]  = -8
    # QQQ
    if   qqq_wk_k < 25: sigs["나스닥 과매도 (역추세 기회)"] = +10
    elif qqq_wk_k > 75: sigs["나스닥 과매수 (시장 경계)"]   = -8
    # 주간 모멘텀
    if   wk_ret >  5: sigs["주간 강한 상승 모멘텀"] = +8
    elif wk_ret >  2: sigs["주간 상승 모멘텀"]      = +5
    elif wk_ret < -5: sigs["주간 강한 하락 모멘텀"] = -8
    elif wk_ret < -2: sigs["주간 하락 모멘텀"]      = -5
    # 월간 추세
    if   mo_ret > 10:  sigs["월간 강세 추세"] = +7
    elif mo_ret >  3:  sigs["월간 상승 추세"] = +4
    elif mo_ret < -10: sigs["월간 강한 하락"] = -7
    elif mo_ret <  -3: sigs["월간 하락 추세"] = -4
    # 이동평균
    sigs["이평선 위 (매수 우위)" if above_ma else "이평선 아래 (매도 우위)"] = +8 if above_ma else -8
    # 신고가 대비
    if   from_hi < -40: sigs["신고가 대비 깊은 조정 (반등 기대)"] = +10
    elif from_hi < -20: sigs["신고가 대비 조정 구간"]             = +4
    elif from_hi >  -5: sigs["신고가 근접 (추가 상승 제한)"]      = -6
    # 거래량
    if vol_ratio > 1.3:
        sigs["거래량 증가 + 상승 (매수 압력)" if wk_ret > 0 else "거래량 증가 + 하락 (매도 압력)"] = +8 if wk_ret > 0 else -8
    # 애널리스트
    net = buy_ratio - sell_ratio
    if   net > 0.5:  sigs["애널리스트 강한 매수 의견"] = +6
    elif net > 0.2:  sigs["애널리스트 매수 우위"]      = +3
    elif net < -0.2: sigs["애널리스트 매도 우위"]      = -6

    score = max(-100, min(100, sum(sigs.values())))
    key   = ("strong_long" if score >= 60 else "long" if score >= 20
             else "strong_short" if score <= -60 else "short" if score <= -20 else "hodl")
    prob  = round(min(95, max(42, 40 + abs(score) * 0.55)), 1)
    return key, score, prob, sigs

# ── 스윙 신호 렌더링 (Streamlit 네이티브 분리 방식) ──────────────────────────
def render_swing_card(key, score, prob, sigs, ticker):
    label, clr, tip = SIGNAL_META[key]

    # 신호명 + 확률 (두 컬럼)
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.markdown(f"""
        <div style="font-size:40px;font-weight:900;color:{clr};letter-spacing:1px;margin-bottom:4px;">
          {label}
        </div>
        <div style="font-size:13px;color:#666;">종합 스코어
          <span style="color:{clr};font-weight:700;">{score:+d} / 100</span>
        </div>
        """, unsafe_allow_html=True)
    with col_b:
        st.markdown(f"""
        <div style="text-align:right;">
          <div style="font-size:12px;color:#555;margin-bottom:2px;">판단 확률</div>
          <div style="font-size:58px;font-weight:900;color:{clr};line-height:1;">{prob}%</div>
        </div>
        """, unsafe_allow_html=True)

    # 5단계 게이지 버튼 형태
    cols = st.columns(5)
    for i, (skey, (slabel, sclr, _)) in enumerate(SIGNAL_META.items()):
        active = (skey == key)
        bg     = sclr if active else "#1e1e30"
        border = f"2px solid {sclr}" if active else "2px solid #2a2a40"
        op     = "1" if active else "0.4"
        cols[i].markdown(f"""
        <div style="text-align:center; padding:8px 4px;
             border-radius:10px; background:{bg}; border:{border}; opacity:{op};
             height:52px;
             display:flex;
             flex-direction:column;
             align-items:center;
             justify-content:center;">
          <div style="font-size:10px; font-weight:900; color:white; line-height:1.3;
               white-space:pre-wrap; word-break:break-word;">
            {slabel.replace(' ', '<br>')}
          </div>
        </div>""", unsafe_allow_html=True)


    # 스코어 바
    bar_left  = 50 if score >= 0 else 50 + score / 2
    bar_width = abs(score) / 2
    st.markdown(f"""
    <div style="margin:14px 0 10px;">
      <div style="background:#1e1e30;border-radius:6px;height:8px;position:relative;">
        <div style="position:absolute;left:50%;top:0;width:2px;height:8px;background:#333;"></div>
        <div style="position:absolute;left:{bar_left:.1f}%;width:{bar_width:.1f}%;
             height:8px;border-radius:6px;background:{clr};"></div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:10px;color:#444;margin-top:4px;">
        <span>STRONG SHORT</span><span>HODL</span><span>STRONG LONG</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # 액션 가이드
    is_short = key in ("strong_short", "short")
    action_icon = "📉" if is_short else ("⏸" if key == "hodl" else "📈")
    action_txt  = (f"{ticker} 숏(Short) 포지션 진입{'을 강하게 권고합니다.' if key=='strong_short' else ' 검토.'}" if is_short
                   else (f"{ticker} 방향성 불명확 — 관망 후 재진입을 기다리세요." if key == "hodl"
                         else f"{ticker} 매수(Long) 포지션 진입{'을 강하게 권고합니다.' if key=='strong_long' else ' 우위 구간.'}"))
    st.markdown(f"""
    <div style="background:#0d0d1e;border-radius:10px;padding:12px 16px;margin:10px 0;">
      <div style="font-size:13px;font-weight:700;color:white;margin-bottom:4px;">
        {action_icon} {action_txt}
      </div>
      <div style="font-size:12px;color:{clr};">💡 {tip}</div>
    </div>""", unsafe_allow_html=True)

    # TOP 신호 요인
    st.markdown("<div style='font-size:11px;color:#555;letter-spacing:1px;margin-bottom:6px;'>TOP 신호 요인</div>",
                unsafe_allow_html=True)
    top5 = sorted([(k,v) for k,v in sigs.items() if v != 0], key=lambda x: abs(x[1]), reverse=True)[:5]
    for s_name, s_val in top5:
        s_clr  = "#30d158" if s_val > 0 else "#e84040"
        s_icon = "▲" if s_val > 0 else "▼"
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
             padding:7px 0;border-bottom:1px solid #1e1e30;font-size:13px;">
          <span style="color:#bbb;">{s_name}</span>
          <span style="color:{s_clr};font-weight:700;">{s_icon} {abs(s_val)}pt</span>
        </div>""", unsafe_allow_html=True)

    # 닫는 태그
    st.markdown("""
    <div style="margin-top:12px;font-size:11px;color:#3a3a4a;">
      ⚠️ 본 신호는 스윙트레이딩 참고용이며 투자 책임은 사용자에게 있습니다.
    </div></div>""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:24px 0 8px;">
  <div style="font-size:28px;font-weight:900;letter-spacing:1px;"> AInvest</div>
  <div style="font-size:13px;color:#555;margin-top:4px;">For Stock</div>
</div>""", unsafe_allow_html=True)

# ── Input ────────────────────────────────────────────────────────────────────
c1, c2 = st.columns(2)
with c1:
    seed_krw = st.number_input("💰 매수 시드 (원)", min_value=10_000,
                                max_value=500_000_000, value=5_000_000,
                                step=100_000, format="%d")
with c2:
    raw_ticker = st.text_input("🔍 분석 종목 (티커)", value="",
                                placeholder="예: AAPL, NVDA, HIMS")

ticker_input = raw_ticker.upper().strip()
if ticker_input:
    st.markdown(f"""
    <div style="background:#1a2a1a;border-radius:10px;padding:10px 16px;
         display:flex;align-items:center;gap:10px;margin-bottom:8px;">
      <span style="font-size:18px;">🇺🇸</span>
      <span style="font-weight:700;font-size:15px;">{ticker_input}</span>
      <span style="color:#30d158;font-size:13px;">✓ 선택됨</span>
    </div>""", unsafe_allow_html=True)

run = st.button("지금 분석하기 →", use_container_width=True)

# ── Analysis ─────────────────────────────────────────────────────────────────
if run and ticker_input:
    with st.spinner("📡 데이터 수집 중 ..."):
        try:
            t   = yf.Ticker(ticker_input)
            inf = t.info
            price     = inf.get("currentPrice") or inf.get("regularMarketPrice") or inf.get("previousClose", 0)
            prev      = inf.get("previousClose") or price
            chg       = price - prev
            chg_pct   = chg / prev * 100 if prev else 0
            name      = inf.get("shortName") or ticker_input
            state_lbl = {"PRE":"🟡 프리마켓","REGULAR":"🟢 정규장",
                         "POST":"🔵 애프터마켓","CLOSED":"⚫ 장 마감"}.get(
                         inf.get("marketState","REGULAR"), "🟢 정규장")

            usd_krw  = get_fx()
            seed_usd = seed_krw / usd_krw

            df_d  = get_hist(ticker_input, "2y",  "1d")
            df_wk = get_hist(ticker_input, "3y",  "1wk")
            df_mo = get_hist(ticker_input, "5y",  "1mo")
            qqq_w = get_hist("QQQ", "3y", "1wk")
            qqq_m = get_hist("QQQ", "5y", "1mo")
            spy_w = get_hist("SPY", "3y", "1wk")

            spy_k,  spy_d  = calc_stoch(spy_w)
            qqqw_k, qqqw_d = calc_stoch(qqq_w)
            qqqm_k, qqqm_d = calc_stoch(qqq_m)
            stk_wk, stk_wd = calc_stoch(df_wk)
            stk_mk, stk_md = calc_stoch(df_mo)

            c_ = df_d["Close"]
            wk_ret = (c_.iloc[-1]/c_.iloc[-6] -1)*100 if len(c_)>=6  else 0
            mo_ret = (c_.iloc[-1]/c_.iloc[-22]-1)*100 if len(c_)>=22 else 0

            lv    = ai_levels(df_d, price)
            buy   = lv["buy"]; sell = lv["sell"]
            qty   = int(seed_usd / buy) if buy > 0 else 0
            tot   = qty * buy
            exp_r = (sell-buy)/buy*100 if buy else 0
            exp_p = qty*(sell-buy)*usd_krw
            mid_tp= (lv["mid_t"]-buy)/buy*100
            lng_tp= (lv["lng_t"]-buy)/buy*100
            mid_dp= (lv["mid_d"]-price)/price*100
            lng_dp= (lv["lng_d"]-price)/price*100

            vol       = df_d["Volume"].dropna()
            vol_ratio = vol.tail(5).sum() / max(vol.tail(100).sum()/20, 1)
            hi52      = df_d["High"].tail(252).max()
            from_hi   = (price/hi52-1)*100
            ma5w      = df_wk["Close"].tail(5).mean()
            above_ma  = price > ma5w
            ma5w_d    = (price-ma5w)/ma5w*100

            try:
                cal = t.calendar
                if cal is not None and "Earnings Date" in cal:
                    ed  = cal["Earnings Date"]
                    ed  = ed[0] if isinstance(ed,(list,tuple)) else ed
                    ed  = pd.Timestamp(ed).date()
                    edd = (ed - date.today()).days
                else:
                    ed = edd = None
            except:
                ed = edd = None

            try:
                ri = t.recommendations
                gc = {"buy":0,"hold":0,"sell":0}
                if ri is not None and len(ri):
                    for _, row in ri.tail(20).iterrows():
                        g = str(row.get("To Grade", row.get("Action",""))).lower()
                        if any(x in g for x in ["buy","outperform","overweight","strong"]):
                            gc["buy"]+=1
                        elif any(x in g for x in ["sell","underperform","underweight"]):
                            gc["sell"]+=1
                        else:
                            gc["hold"]+=1
                else:
                    gc = {"buy":3,"hold":11,"sell":1}
            except:
                gc = {"buy":3,"hold":11,"sell":1}
            tc = sum(gc.values()) or 1

            tmed  = inf.get("targetMedianPrice") or inf.get("targetMeanPrice") or 0
            tlow  = inf.get("targetLowPrice")  or 0
            thigh = inf.get("targetHighPrice") or 0
            upside= (tmed/price-1)*100 if tmed and price else 0

            rs, rf = risk_score(stk_wk, vol_ratio, above_ma, gc["sell"]/tc)
            r_lbl  = "저위험" if rs<=30 else ("중위험" if rs<=60 else "고위험")
            r_clr  = "#30d158" if rs<=30 else ("#ff9500" if rs<=60 else "#e84040")
            r_desc = ("매수 적합 구간. 상대적으로 안전해요." if rs<=30
                      else ("주의 구간. 분할 진입을 고려하세요." if rs<=60
                            else "위험 구간. 신중하게 접근하세요."))

            sig_key, sig_score, sig_prob, sig_details = swing_signal(
                stk_wk, stk_wd, stk_mk, stk_md,
                qqqw_k, wk_ret, mo_ret, above_ma,
                vol_ratio, from_hi, gc["buy"]/tc, gc["sell"]/tc
            )

            # ═══════════════════════ RENDER ══════════════════════════════
            st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

            # 현재가
            chg_c = "#e84040" if chg>=0 else "#4a9eff"
            arrow = "▲" if chg>=0 else "▼"
            st.markdown(f"""
            <div class="card">
              <div class="lbl">{state_lbl} &nbsp;·&nbsp; {name} ({ticker_input})</div>
              <div style="font-size:38px;font-weight:900;color:white;margin:4px 0;">${price:,.2f}</div>
              <div style="font-size:14px;color:{chg_c};">
                {arrow} {abs(chg):.2f} ({chg_pct:+.2f}%)
                <span style="color:#555;font-size:12px;margin-left:12px;">전일종가 ${prev:,.2f}</span>
              </div>
            </div>""", unsafe_allow_html=True)

            # ══ 스윙 신호 ══
            st.markdown("<div class='section-title'>🎯 스윙 트레이딩 신호</div>", unsafe_allow_html=True)
            render_swing_card(sig_key, sig_score, sig_prob, sig_details, ticker_input)

            # 시장 추세
            st.markdown("<div class='section-title'>📊 시장 추세</div>", unsafe_allow_html=True)
            st.markdown(stoch_html("시장 추세 (SPY 주봉)", spy_k, spy_d), unsafe_allow_html=True)
            st.markdown(stoch_html("나스닥 주간 (QQQ 주봉)", qqqw_k, qqqw_d), unsafe_allow_html=True)
            st.markdown(stoch_html("나스닥 월간 (QQQ 월봉)", qqqm_k, qqqm_d), unsafe_allow_html=True)

            st.markdown(f"<div class='section-title'>📈 {ticker_input} 스토캐스틱</div>", unsafe_allow_html=True)
            st.markdown(stoch_html(f"{ticker_input} 주간", stk_wk, stk_wd), unsafe_allow_html=True)
            st.markdown(stoch_html(f"{ticker_input} 월간", stk_mk, stk_md), unsafe_allow_html=True)

            # AI 매매전략
            st.markdown("<div class='section-title'>💡 AI 매매 전략</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""<div class="card">
                  <div class="lbl">매수 · 중심선 (AI)</div>
                  <div style="font-size:30px;font-weight:900;color:#e84040;">${buy:,.2f}</div>
                  <div class="sub">진입가 ({(buy/price-1)*100:+.1f}%)</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="card">
                  <div class="lbl">매도 · 1차 목표 (AI)</div>
                  <div style="font-size:30px;font-weight:900;color:#4a9eff;">${sell:,.2f}</div>
                  <div class="sub">목표가 ({(sell/price-1)*100:+.1f}%)</div>
                </div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""<div class="card">
                  <div class="lbl">수량 / 총액</div>
                  <div style="font-size:30px;font-weight:900;color:white;">{qty:,}주</div>
                  <div class="sub">≈ {tot*usd_krw:,.0f}원</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                ec = "#e84040" if exp_r>=0 else "#4a9eff"
                st.markdown(f"""<div class="card">
                  <div class="lbl">예상 수익률</div>
                  <div style="font-size:30px;font-weight:900;color:{ec};">{exp_r:+.2f}%</div>
                  <div class="sub">{'+' if exp_p>=0 else ''}{exp_p/10000:.0f}만원</div>
                </div>""", unsafe_allow_html=True)

            # 목표가/방어선
            st.markdown("<div class='section-title'>🎯 목표가 &amp; 방어선</div>", unsafe_allow_html=True)
            st.markdown(pct_bar_html("중기 목표", "📅", lv["mid_t"], mid_tp, "이 가격을 돌파하면 추가 상승이 기대돼요"), unsafe_allow_html=True)
            st.markdown(pct_bar_html("장기 목표", "📅", lv["lng_t"], lng_tp, "상승 추세가 강할 때 노릴 수 있어요"), unsafe_allow_html=True)
            st.markdown(pct_bar_html("중기 방어선", "🛡️", lv["mid_d"], mid_dp, "이 가격 아래로 내려가면 추가 하락 위험이 있어요", False), unsafe_allow_html=True)
            st.markdown(pct_bar_html("장기 방어선", "🔒", lv["lng_d"], lng_dp, "핵심 지지 구간 · 이탈 시 추세 전환 가능성", False), unsafe_allow_html=True)

            # 기술적 지표
            st.markdown("<div class='section-title'>📐 기술적 지표</div>", unsafe_allow_html=True)
            vol_c   = "#ff9500" if vol_ratio>=1.3 else "white"
            st.markdown(f"""<div class="card">
              <div class="lbl">📊 이번 주 거래량</div>
              <div style="font-size:30px;font-weight:900;color:{vol_c};">{vol_ratio:.1f}배</div>
              <div class="sub">20주 평균 대비 · {'거래량이 늘었어요.' if vol_ratio>1.2 else '거래량 평균 수준이에요.'}</div>
            </div>""", unsafe_allow_html=True)

            prog_w = max(0, 100+from_hi)
            hi_lbl = "반토막 이상" if from_hi<-50 else ("신고가 근접" if from_hi>-10 else "")
            st.markdown(f"""<div class="card">
              <div class="lbl">📉 52주 신고가 대비</div>
              <div style="font-size:26px;font-weight:900;color:#4a9eff;">{from_hi:.1f}% {hi_lbl}</div>
              <div style="background:#222;border-radius:4px;height:6px;margin:8px 0;">
                <div style="width:{prog_w:.0f}%;background:#888;height:6px;border-radius:4px;"></div>
              </div>
            </div>""", unsafe_allow_html=True)

            ma_c = "#e84040" if above_ma else "#4a9eff"
            st.markdown(f"""<div class="card">
              <div class="lbl">📊 5주 이동평균선</div>
              <div style="font-size:24px;font-weight:900;color:{ma_c};">{'5주선 위 ↗' if above_ma else '5주선 아래 ↘'}</div>
              <div style="background:{'#4a1a1a' if above_ma else '#1a2050'};border-radius:5px;
                   padding:3px 12px;display:inline-block;margin:6px 0;">
                <span style="color:{ma_c};font-weight:700;">{ma5w_d:+.1f}%</span>
              </div>
              <div class="sub">{'단기 추세 살아있어요. 매수 우위.' if above_ma else '단기 추세 약화. 신중한 접근.'}</div>
            </div>""", unsafe_allow_html=True)

            # 실적
            earn_str = (f"D-{edd}" if edd and edd>0 else (f"D+{abs(edd)}" if edd and edd<0 else ("오늘!" if edd==0 else "미확인")))
            st.markdown(f"""<div class="card">
              <div class="lbl">📅 다음 실적 발표</div>
              <div style="font-size:40px;font-weight:900;color:white;">{earn_str}</div>
              <div class="sub">{str(ed) if ed else '일정 미확인'}</div>
            </div>""", unsafe_allow_html=True)

            # 컨센서스
            st.markdown("<div class='section-title'>🧑‍💼 애널리스트 컨센서스</div>", unsafe_allow_html=True)
            up_c = "#e84040" if upside>=0 else "#4a9eff"
            st.markdown(f"""<div class="card">
              <div style="display:flex;gap:24px;margin-bottom:10px;">
                <div>
                  <div class="lbl">목표가 (중앙값)</div>
                  <div style="font-size:24px;font-weight:900;color:white;">${tmed:,.2f}</div>
                </div>
                <div>
                  <div class="lbl">목표가 레인지</div>
                  <div style="font-size:16px;font-weight:700;color:white;margin-top:6px;">${tlow:,.2f} ~ ${thigh:,.2f}</div>
                </div>
              </div>
              <div style="color:{up_c};font-weight:700;font-size:14px;margin-bottom:10px;">{upside:+.1f}% 업사이드</div>
              <div style="font-size:12px;color:#666;margin-bottom:6px;">
                ({tc}명) &nbsp;
                <span style="color:#e84040;">매수 {gc['buy']}</span> ·
                <span style="color:#888;">보유 {gc['hold']}</span> ·
                <span style="color:#4a9eff;">매도 {gc['sell']}</span>
              </div>
              <div style="background:#2a2a40;border-radius:5px;height:8px;overflow:hidden;">
                <div style="display:flex;height:100%;">
                  <div style="width:{gc['buy']/tc*100:.0f}%;background:#e84040;"></div>
                  <div style="width:{gc['hold']/tc*100:.0f}%;background:#444;"></div>
                  <div style="width:{gc['sell']/tc*100:.0f}%;background:#4a9eff;"></div>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

            # 리스크
            st.markdown("<div class='section-title'>🛡️ 리스크 스코어</div>", unsafe_allow_html=True)
            factors_html = "".join([
                f"""<div style="display:flex;justify-content:space-between;padding:6px 0;
                    border-bottom:1px solid #1e1e30;font-size:13px;">
                  <span style="color:#ccc;">{k}</span>
                  <span style="color:{'#30d158' if v==0 else '#e84040'};font-weight:700;">
                    {'+'+str(v) if v>0 else str(v)}
                  </span></div>"""
                for k, v in rf.items()
            ])
            st.markdown(f"""<div class="card">
              <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
                <span style="font-size:36px;font-weight:900;color:{r_clr};">{rs}</span>
                <span style="color:#555;font-size:14px;">/100</span>
                <span style="font-size:16px;font-weight:900;color:{r_clr};">{r_lbl}</span>
              </div>
              <div class="sub" style="margin-bottom:10px;">{r_desc}</div>
              <div style="background:#2a2a40;border-radius:5px;height:8px;margin-bottom:14px;">
                <div style="width:{rs}%;background:{r_clr};border-radius:5px;height:8px;"></div>
              </div>
              <div style="font-size:12px;color:#555;margin-bottom:6px;">기여 요소</div>
              {factors_html}
            </div>""", unsafe_allow_html=True)

            st.markdown("""
            <div style="background:#0f0f1e;border:1px solid #2a2a40;border-radius:10px;
                 padding:12px 16px;margin-top:16px;font-size:12px;color:#555;">
              ⚠️ 본 분석은 투자 참고용이며 투자 결정의 책임은 사용자에게 있습니다.
            </div>""", unsafe_allow_html=True)

        except Exception as e:
            st.markdown("""
            <div style="background:#1a0f0f;border:1px solid #e84040;border-radius:14px;
                 padding:20px 22px;margin-top:12px;">
              <div style="font-size:16px;font-weight:900;color:#e84040;margin-bottom:12px;">
                ⚠️ 종목을 찾을 수 없어요
              </div>
              <div style="font-size:13px;color:#aaa;line-height:2;margin-bottom:14px;">
                티커 심볼을 다시 확인해주세요.<br>
                한글 종목명으로는 검색이 되지 않아요.
              </div>
              <div style="background:#0f0f1e;border-radius:10px;padding:14px 16px;">
                <div style="font-size:12px;color:#ff9500;font-weight:700;
                     margin-bottom:10px;letter-spacing:1px;">💡 검색 TIP</div>
                <div style="font-size:12px;color:#888;line-height:2.2;">
                  🇺🇸 &nbsp;미국 주식 &nbsp;→&nbsp;
                    <span style="color:white;font-weight:700;">AAPL, NVDA, TSLA</span><br>
                  🇰🇷 &nbsp;국내 주식 &nbsp;→&nbsp;
                    <span style="color:white;font-weight:700;">005930.KS</span>
                    <span style="color:#555;">&nbsp;(삼성전자)</span><br>
                  🇰🇷 &nbsp;코스닥 &nbsp;&nbsp;&nbsp;→&nbsp;
                    <span style="color:white;font-weight:700;">035720.KQ</span>
                    <span style="color:#555;">&nbsp;(카카오)</span><br>
                  📊 &nbsp;ETF &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;→&nbsp;
                    <span style="color:white;font-weight:700;">QQQ, SPY, SOXS</span>
                </div>
              </div>
            </div>""", unsafe_allow_html=True)

=======
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
>>>>>>> 808eb64679000f6bc300bfc73de95747ebbe02ef
