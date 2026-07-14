#!/usr/bin/env python3
"""분석2: 스타일·팩터 노출. (fund-SPY) 초과수익을 스타일 스프레드에 회귀해 틸트 측정.
팩터: 성장-가치(IWF-IWD), 사이즈(IWM-SPY), 모멘텀(MTUM-SPY), 퀄리티(QUAL-SPY), 암호화폐(BITO)."""
import os, numpy as np, pandas as pd, yfinance as yf, statsmodels.api as sm
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
tk=["NANC","GOP","SPY","IWF","IWD","IWM","MTUM","QUAL","BITO"]; SPLIT="2025-01-17"
px=yf.download(tk,start="2023-02-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"].dropna()
r=px.pct_change().dropna()
F=pd.DataFrame({
 "성장-가치":r["IWF"]-r["IWD"],
 "사이즈(소형)":r["IWM"]-r["SPY"],
 "모멘텀":r["MTUM"]-r["SPY"],
 "퀄리티":r["QUAL"]-r["SPY"],
 "암호화폐":r["BITO"],
})
eras={"바이든":(None,SPLIT),"트럼프2기":(SPLIT,None),"전체":(None,None)}
for ename,(s,e) in eras.items():
    print("="*60); print(f"[{ename}]  (fund-SPY) ~ 팩터")
    idx=F.index
    if s: idx=idx[idx>=pd.Timestamp(s)]
    if e: idx=idx[idx<=pd.Timestamp(e)]
    X=sm.add_constant(F.loc[idx])
    for f in ["NANC","GOP"]:
        y=(r[f]-r["SPY"]).loc[idx]
        m=sm.OLS(y,X).fit()
        coefs=" ".join([f"{c}={m.params[c]:+.2f}{'*' if abs(m.tvalues[c])>2 else ''}" for c in F.columns])
        print(f"  {f}: {coefs}   (R²={m.rsquared:.2f}, 알파연율={((1+m.params['const'])**252-1)*100:+.1f}%)")
    print("   (* = |t|>2 유의, 알파=초과수익 중 팩터로 설명 안 되는 부분)")
    print()
print("해석: 성장-가치 계수 +면 성장주 틸트, 사이즈+ 소형주, 암호화폐+ 코인 노출")
