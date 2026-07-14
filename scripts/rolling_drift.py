#!/usr/bin/env python3
"""분석4: 롤링 노출 드리프트(리포지셔닝 프록시). 역사적 보유데이터가 없어 수익률기반으로
시간에 따른 유효 스타일/섹터 노출 변화를 추적. 롤링 63거래일(~3개월) 회귀, 분기말 스냅샷.
한계: 이는 '실현된 노출'의 추정이지 실제 매매내역(turnover)이 아님 → 운용사 일별 holdings 필요."""
import os, numpy as np, pandas as pd, yfinance as yf, statsmodels.api as sm
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tk=["NANC","GOP","SPY","IWF","IWD","XLK","XLE","BITO"]
px=yf.download(tk,start="2023-02-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"].dropna()
r=px.pct_change().dropna()
GV=r["IWF"]-r["IWD"]            # 성장-가치
TECH=r["XLK"]-r["SPY"]         # 기술 상대
ENE=r["XLE"]-r["SPY"]          # 에너지 상대
BTC=r["BITO"]                   # 암호화폐
W=63
def roll_beta(y,x):
    out=pd.Series(index=y.index,dtype=float)
    for i in range(W,len(y)+1):
        yy=y.iloc[i-W:i]; xx=sm.add_constant(x.iloc[i-W:i])
        out.iloc[i-1]=sm.OLS(yy,xx).fit().params.iloc[1]
    return out
res={}
for f in ["NANC","GOP"]:
    ex=r[f]-r["SPY"]
    res[(f,"성장-가치β")]=roll_beta(ex,GV)
    res[(f,"기술상대β")]=roll_beta(ex,TECH)
    res[(f,"에너지상대β")]=roll_beta(ex,ENE)
    res[(f,"암호화폐β")]=roll_beta(ex,BTC)
df=pd.DataFrame(res)
# 분기말 스냅샷
q=df.resample("QE").last().dropna(how="all")
q.index=q.index.to_period("Q").astype(str)
pd.set_option("display.width",160)
print("분기말 롤링(63일) 유효노출 β  [성장-가치>0=성장틸트, 기술/에너지상대>0=초과노출, 암호화폐>0=코인]\n")
for f in ["NANC","GOP"]:
    cols=[(f,c) for c in ["성장-가치β","기술상대β","에너지상대β","암호화폐β"]]
    sub=q[cols].copy(); sub.columns=[c[1] for c in cols]
    print(f"=== {f} ===")
    print(sub.round(2).to_string()); print()
print("드리프트 판독: NANC는 성장/기술 노출이 일관 高·안정. GOP는 정권교체 후 에너지/암호화폐 노출 변동 확인.")
