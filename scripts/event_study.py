#!/usr/bin/env python3
"""분석3: 정책 이벤트 스터디. 주요 정책일 전후 NANC/GOP의 누적수익 및 SPY 대비 초과수익.
이벤트일 직전 거래일 종가를 기준(0), 이후 +k일 누적. 초과수익=fund-SPY (스타일이 정책에 반응한 정도)."""
import os, pandas as pd, yfinance as yf
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
px=yf.download(["NANC","GOP","SPY"],start="2023-02-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"].dropna()

EVENTS={
 "2024 대선 트럼프 승리(11/6)":"2024-11-06",
 "Fed 첫 인하 50bp(9/18)":"2024-09-18",
 "트럼프 2기 취임 첫거래일(1/21)":"2025-01-21",
 "전략적 비트코인 비축 EO(3/6)":"2025-03-06",
 "해방의날 상호관세(4/3~4)":"2025-04-03",
 "90일 관세유예 랠리(4/9)":"2025-04-09",
}
def fwd(d,k):
    idx=px.index
    pos=idx.searchsorted(pd.Timestamp(d))   # first idx >= d
    if pos>=len(idx): return None
    base=pos-1 if pos>0 else 0
    end=min(base+k,len(idx)-1)
    p0=px.iloc[base]; p1=px.iloc[end]
    return (p1/p0-1)*100, idx[base].date(), idx[end].date()

print(f"{'이벤트':<34}{'창':>5}{'NANC':>8}{'GOP':>8}{'SPY':>8}{'NANC-SPY':>10}{'GOP-SPY':>10}")
print("-"*83)
for lbl,d in EVENTS.items():
    for k in [1,5]:
        res=fwd(d,k)
        if not res: continue
        r,d0,d1=res
        nx=r["NANC"]-r["SPY"]; gx=r["GOP"]-r["SPY"]
        tag=f"+{k}일"
        name=lbl if k==1 else ""
        print(f"{name:<34}{tag:>5}{r['NANC']:>+8.1f}{r['GOP']:>+8.1f}{r['SPY']:>+8.1f}{nx:>+10.1f}{gx:>+10.1f}")
    print()
print("해석: 초과수익(fund-SPY) 부호로 어느 펀드 스타일이 그 정책에 더 반응했는지 판별")
