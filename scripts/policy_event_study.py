#!/usr/bin/env python3
"""정책이벤트 스터디 — CHIPS·관세 → 해당 (하위)섹터 초과수익(vs SPY).
사전런업[-63,0](시장이 미리 반영했나) + 사후 +1w/+1m/+3m/+6m/+1y/현재까지(다년 추종).
시장조정(−SPY) CAR. 한계: 교란·기대선반영 가능, 단일이벤트."""
import numpy as np,pandas as pd,yfinance as yf
T=["SMH","SOXX","XLK","XLI","SLX","XLE","XLF","INTC","NVDA","AAPL","SPY"]
px=yf.download(T,start="2022-01-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"].dropna(how="all")
idx=px.index
def car(tk,date,h):  # 이벤트 다음거래일~+h거래일, SPY 대비 초과(%). h=None→현재까지, h<0→사전런업
    if tk not in px or pd.isna(px[tk]).all(): return None
    pos=idx.searchsorted(pd.Timestamp(date))
    if pos>=len(idx): return None
    if h is None: e=len(idx)-1; b=pos
    elif h<0: b=max(0,pos+h); e=pos
    else: b=pos; e=min(pos+h,len(idx)-1)
    s=px[tk]
    if pd.isna(s.iloc[b]) or pd.isna(s.iloc[e]) or b>=e: return None
    return ((s.iloc[e]/s.iloc[b]-1)-(px["SPY"].iloc[e]/px["SPY"].iloc[b]-1))*100
EV=[
 ("CHIPS법 서명(22-08-09)","2022-08-09",[("반도체","SMH")]),
 ("對中 반도체 수출통제(22-10-07)","2022-10-07",[("반도체","SMH")]),
 ("인텔 정부지분(25-08-22)","2022-08-22" if False else "2025-08-22",[("인텔","INTC"),("반도체","SMH")]),
 ("해방의날 상호관세(25-04-02)","2025-04-02",[("기술","XLK"),("산업재","XLI"),("철강","SLX"),("에너지","XLE")]),
 ("90일 관세유예(25-04-09)","2025-04-09",[("기술","XLK"),("반도체","SMH"),("산업재","XLI")]),
]
HOR=[("-63d 사전",-63),("+1w",5),("+1m",21),("+3m",63),("+6m",126),("+1y",252),("현재",None)]
print("정책이벤트 → 해당섹터 초과수익(vs SPY, %). 음수 사전 = 기대선반영 여부\n")
print(f"{'이벤트 / 섹터':<34}"+"".join(f"{h[0]:>8}" for h in HOR)); print("-"*92)
for lab,d,baskets in EV:
    print(lab)
    for nm,tk in baskets:
        vals=[car(tk,d,h) for _,h in HOR]
        print(f"   └ {nm:<28}"+"".join((f"{v:>+8.0f}" if v is not None else f"{'·':>8}") for v in vals))
    print()
