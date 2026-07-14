#!/usr/bin/env python3
"""'알파 = 정책발 섹터 틸트' 가설 정식 검증.
가설: ETF의 SPY대비 초과수익은 '집권당 정책 수혜섹터' 노출로 설명되고, 잔차알파≈0.
정책 테마(섹터-SPY 초과수익) 팩터:
  반도체 SMH, 기술 XLK  [바이든: CHIPS/IRA/AI]
  에너지 XLE, 금융 XLF, 산업재 XLI, 암호화폐 BITO  [트럼프: 시추/규제완화/관세리쇼어링/크립토]"""
import os, numpy as np, pandas as pd, yfinance as yf, statsmodels.api as sm
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
tk=["NANC","GOP","SPY","SMH","XLK","XLE","XLF","XLI","BITO"]; SPLIT="2025-01-17"
px=yf.download(tk,start="2023-02-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"].dropna()
r=px.pct_change().dropna()
# 정책 테마 = 섹터 초과수익(섹터-SPY)
TH={"반도체":r["SMH"]-r["SPY"],"기술":r["XLK"]-r["SPY"],"에너지":r["XLE"]-r["SPY"],
    "금융":r["XLF"]-r["SPY"],"산업재":r["XLI"]-r["SPY"],"암호화폐":r["BITO"]-r["SPY"]}
F=pd.DataFrame(TH)
BIDEN_THEMES=["반도체","기술"]; TRUMP_THEMES=["에너지","금융","산업재","암호화폐"]
eras={"바이든":(None,SPLIT,BIDEN_THEMES),"트럼프2기":(SPLIT,None,TRUMP_THEMES)}

print("STEP1 — 각 정권의 '정책 수혜섹터'는 실제로 SPY를 이겼나? (구간 누적 초과수익)")
for ename,(s,e,themes) in eras.items():
    idx=F.index
    if s: idx=idx[idx>=pd.Timestamp(s)]
    if e: idx=idx[idx<=pd.Timestamp(e)]
    print(f"  [{ename}]  정책섹터:",", ".join(f"{th} {((1+F[th].loc[idx]).prod()-1)*100:+.1f}%p" for th in themes))
print()

print("STEP2 — ETF 초과수익(ETF-SPY)을 '정책 테마'에 회귀  [정책으로 설명되면 알파→0]")
for ename,(s,e,themes) in eras.items():
    idx=F.index
    if s: idx=idx[idx>=pd.Timestamp(s)]
    if e: idx=idx[idx<=pd.Timestamp(e)]
    X=sm.add_constant(F[themes].loc[idx])
    print(f"\n  [{ename}]  (정책테마: {', '.join(themes)})")
    for f in ["NANC","GOP"]:
        y=(r[f]-r["SPY"]).loc[idx]
        m=sm.OLS(y,X).fit()
        betas=" ".join(f"{th}={m.params[th]:+.2f}{'*' if abs(m.tvalues[th])>2 else ''}" for th in themes)
        a_ann=((1+m.params['const'])**252-1)*100
        print(f"    {f}: {betas} | R²={m.rsquared:.2f} 잔차알파={a_ann:+.1f}%(t={m.tvalues['const']:.1f})")
print("\n(* |t|>2 유의. 잔차알파≈0 & 정책테마 유의 → '알파=정책 섹터틸트' 확증)")

print("\nSTEP3 — 구간 누적 초과수익을 '정책섹터 기여 vs 잔차'로 분해")
for ename,(s,e,themes) in eras.items():
    idx=F.index
    if s: idx=idx[idx>=pd.Timestamp(s)]
    if e: idx=idx[idx<=pd.Timestamp(e)]
    X=sm.add_constant(F[themes].loc[idx])
    for f in ["NANC","GOP"]:
        y=(r[f]-r["SPY"]).loc[idx]
        m=sm.OLS(y,X).fit()
        total=((1+y).prod()-1)*100
        # 정책기여 = 적합값 누적, 잔차 = 알파+오차 누적
        fitted_ex_alpha=(X[themes]*[m.params[t] for t in themes]).sum(axis=1)
        policy=((1+fitted_ex_alpha).prod()-1)*100
        print(f"  [{ename}] {f}: 총초과 {total:+.1f}%p ≈ 정책섹터기여 {policy:+.1f}%p + 잔차 {total-policy:+.1f}%p")
