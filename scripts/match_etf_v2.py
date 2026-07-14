#!/usr/bin/env python3
"""ETF 일치도 점검 v2 — 'cost-basis 가중' vs 'market-value(시가) 가중' 비교.
가설: ETF는 보유 포지션의 현재 시가로 가중(승자가 커짐) → 거래를 주식수로 환산해 현재가치 재구성.
순주식수 = Σ(매수$/매수가) - Σ(매도$/매도가),  현재가치 = 순주식수 × 현재가.
실제 ETF top보유(yfinance)와 비중상관 비교."""
import os, numpy as np, pandas as pd, yfinance as yf
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
df=pd.read_csv(os.path.join(DATA,"combined_2019_2026.csv"),parse_dates=["transaction_date"])
df["amount"]=pd.to_numeric(df["amount"],errors="coerce")
df=df.dropna(subset=["amount"])
px=pd.read_csv(os.path.join(DATA,"ptr_prices.csv"),index_col=0,parse_dates=True)
# 누락 티커 보충
need=sorted({t.replace(".","-") for t in df.ticker.unique()} - set(px.columns))
if need:
    for i in range(0,len(need),150):
        d=yf.download(need[i:i+150],start="2019-01-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
        px=pd.concat([px,d],axis=1)
    px=px.loc[:,~px.columns.duplicated()]; px.to_csv(os.path.join(DATA,"ptr_prices.csv"))
idx=px.index
def price_at(t,d):
    yt=t.replace(".","-")
    if yt not in px.columns: return None
    s=px[yt].dropna(); s=s[s.index<=pd.Timestamp(d)]
    return s.iloc[-1] if len(s) else None
def cur(t):
    yt=t.replace(".","-")
    if yt not in px.columns: return None
    s=px[yt].dropna(); return s.iloc[-1] if len(s) else None

def actual(tkr):
    th=yf.Ticker(tkr).funds_data.top_holdings
    s=(th["Holding Percent"]*100); s.index=[i.replace("-",".") for i in s.index]; return s
NANC_act=actual("NANC"); GOP_act=actual("GOP")

def shadow_mv(party, since="2023-01-01", cap=12.0, top=150):
    d=df[(df.party==party)&(df.transaction_date>=pd.Timestamp(since))].copy()
    sh={}
    for _,r in d.iterrows():
        p=price_at(r.ticker,r.transaction_date)
        if not p or p<=0: continue
        q=r.amount/p*(1 if r.type=="P" else -1 if r.type=="S" else 0)
        sh[r.ticker]=sh.get(r.ticker,0)+q
    val={t:s*cur(t) for t,s in sh.items() if cur(t) and s>0}
    s=pd.Series(val); s=s[s>0].sort_values(ascending=False).head(top)
    if s.sum()<=0: return pd.Series(dtype=float)
    w=s/s.sum()*100
    for _ in range(60):
        over=w>cap
        if not over.any(): break
        ex=(w[over]-cap).sum(); w[over]=cap; w[~over]+=ex*w[~over]/w[~over].sum()
    return w.round(2)
def shadow_cost(party, since="2023-01-01", cap=12.0, top=150):
    d=df[(df.party==party)&(df.transaction_date>=pd.Timestamp(since))]
    net=d.assign(sgn=np.where(d.type=="P",d.amount,-d.amount)).groupby("ticker").sgn.sum()
    net=net[net>0].sort_values(ascending=False).head(top); w=net/net.sum()*100
    for _ in range(60):
        over=w>cap
        if not over.any(): break
        ex=(w[over]-cap).sum(); w[over]=cap; w[~over]+=ex*w[~over]/w[~over].sum()
    return w.round(2)

def comp(name,act,party):
    print("\n"+"="*64); print(f"[{name}] (정당 {party}, 2023~)"); print("="*64)
    for lab,sw in [("cost-basis",shadow_cost(party)),("market-value",shadow_mv(party))]:
        hit=[t for t in act.index if t in sw.index]
        corr=np.corrcoef([act[t] for t in hit],[sw[t] for t in hit])[0,1] if len(hit)>=3 else np.nan
        print(f"  {lab:13}: 이름 {len(hit)}/{len(act)} | 비중상관 {corr:+.2f} | top8: "+", ".join(f"{t} {v:.0f}%" for t,v in sw.head(8).items()))
    print("  실제:        "+", ".join(f"{t} {v:.0f}%" for t,v in act.items()))
comp("NANC",NANC_act,"D"); comp("GOP",GOP_act,"R")
