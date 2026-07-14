#!/usr/bin/env python3
"""정책→섹터 로테이션 — 1/2/3년 forward 확장 (호라이즌 지적 반영).
저장된 섹터-연도 정책신호(netbuy·reg) 재사용 + ETF 다년 누적 초과수익. 정책 t → 섹터수익 t→t+h."""
import os,numpy as np,pandas as pd,yfinance as yf
from scipy.stats import pearsonr
DATA=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"data")
p=pd.read_csv(os.path.join(DATA,"sector_rotation.csv"))[["theme","year","netbuy","reg"]]
ETF={"기술/반도체":"XLK","금융":"XLF","헬스케어":"XLV","에너지":"XLE","산업재":"XLI","커뮤니케이션":"XLC","필수소비재":"XLP","소재":"XLB"}
p["etf"]=p.theme.map(ETF)
px=yf.download(list(set(ETF.values()))+["SPY"],start="2019-06-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
ye=px.resample("YE").last(); ye.index=ye.index.year; last={c:px[c].dropna().iloc[-1] for c in px}
def fwd(etf,y,h):
    if y+h in ye.index and not pd.isna(ye.loc[y,etf]):
        return ((ye.loc[y+h,etf]/ye.loc[y,etf]-1)-(ye.loc[y+h,"SPY"]/ye.loc[y,"SPY"]-1))*100
    if (y+h>2025) and not pd.isna(ye.loc[y,etf]):  # 미래연말 없으면 최신가로 (부분)
        return ((last[etf]/ye.loc[y,etf]-1)-(last["SPY"]/ye.loc[y,"SPY"]-1))*100
    return None
for h in [1,2,3]:
    p[f"fwd{h}"]=[fwd(e,y,h) for e,y in zip(p.etf,p.year)]
def z(s): return (s-s.mean())/s.std() if s.std()>0 else s*0
p["pol"]=z(p.netbuy)+z(p.reg)
print("정책 t → 섹터 누적초과수익 t→t+h (섹터=단위, 중립화 없음)\n")
print(f"{'호라이즌':<8}{'n':>4}{'순매수 r':>11}{'규제 r':>10}{'결합 r':>10}{'강한-약한 격차':>16}")
for h in [1,2,3]:
    s=p.dropna(subset=[f"fwd{h}"])
    rn=pearsonr(s.netbuy,s[f"fwd{h}"]); rr=pearsonr(s.reg,s[f"fwd{h}"]); rp=pearsonr(s.pol,s[f"fwd{h}"])
    hi=s[s.pol>=s.pol.median()][f"fwd{h}"].mean(); lo=s[s.pol<s.pol.median()][f"fwd{h}"].mean()
    star=lambda pv:"*" if pv<0.05 else ""
    print(f"+{h}년     {len(s):>4}{rn[0]:>+8.2f}{star(rn[1])}{rr[0]:>+9.2f}{star(rr[1])}{rp[0]:>+9.2f}{star(rp[1])}   {hi:+.0f}% vs {lo:+.0f}%")
print("\n(선행 r이 호라이즌 길수록 ↑·유의 → 다년 정책-섹터 로테이션 예측력. 계속 ~0 → 다년에도 선행력 없음)")
# 대표 사례: CHIPS→반도체
print("\n사례 — 기술/반도체 정책신호 vs 다년수익:")
for _,r in p[p.theme=="기술/반도체"].sort_values("year").iterrows():
    print(f"  {int(r.year)}: 순매수 {r.netbuy:+.1f}M, 규제 {int(r.reg)} → +1y {r.fwd1 if pd.isna(r.fwd1) else round(r.fwd1)}%, +2y {r.fwd2 if pd.isna(r.fwd2) else round(r.fwd2)}%, +3y {r.fwd3 if pd.isna(r.fwd3) else round(r.fwd3)}%")
