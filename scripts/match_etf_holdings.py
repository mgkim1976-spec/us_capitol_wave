#!/usr/bin/env python3
"""실제 ETF 보유 vs 의회거래 재구성(shadow) 일치도 점검.
shadow: 정당별(D→NANC, R→GOP) 순매수금액(buys-sells, 중간값) 가중 = 운용사 '총투입금액' 규칙 근사.
두 윈도: 전체(2019~) / 최근(2023~, 현직 근접). 실제 ETF top보유는 yfinance에서 최신 재취득."""
import os, numpy as np, pandas as pd, yfinance as yf
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
df=pd.read_csv(os.path.join(DATA,"combined_2019_2026.csv"),parse_dates=["transaction_date"])
df["amount"]=pd.to_numeric(df["amount"],errors="coerce")
df["signed"]=np.where(df.type=="P",df.amount,np.where(df.type=="S",-df.amount,0))

# ---- 실제 ETF 보유 (yfinance 최신) ----
def actual(tkr):
    th=yf.Ticker(tkr).funds_data.top_holdings  # Symbol index, Holding Percent
    s=(th["Holding Percent"]*100); s.index=[i.replace("-",".") for i in s.index]
    return s
NANC_act=actual("NANC"); GOP_act=actual("GOP")
print("실제 NANC top:",", ".join(f"{t} {v:.1f}%" for t,v in NANC_act.items()))
print("실제 GOP  top:",", ".join(f"{t} {v:.1f}%" for t,v in GOP_act.items()))

def shadow(party, since=None, cap=10.0, top=150):
    d=df[df.party==party]
    if since: d=d[d.transaction_date>=pd.Timestamp(since)]
    net=d.groupby("ticker")["signed"].sum()
    net=net[net>0].sort_values(ascending=False).head(top)
    if net.sum()<=0: return pd.Series(dtype=float)
    w=net/net.sum()*100
    for _ in range(60):
        over=w>cap
        if not over.any(): break
        ex=(w[over]-cap).sum(); w[over]=cap; w[~over]+=ex*w[~over]/w[~over].sum()
    return w.round(2)

def compare(name, act, party):
    print("\n"+"="*64); print(f"[{name}] 실제 vs shadow(정당 {party})"); print("="*64)
    for label,since in [("전체2019~",None),("최근2023~","2023-01-01")]:
        sw=shadow(party,since)
        hit=[t for t in act.index if t in sw.index]
        hit30=[t for t in act.index if t in sw.head(30).index]
        corr=np.corrcoef([act[t] for t in hit],[sw[t] for t in hit])[0,1] if len(hit)>=3 else np.nan
        print(f"\n  · {label}: 실제 top{len(act)} 중 shadow존재 {len(hit)}/{len(act)} | shadow상위30내 {len(hit30)}/{len(act)} | 비중상관 {corr:+.2f}")
        print(f"    shadow top12: "+", ".join(f"{t} {v}%" for t,v in sw.head(12).items()))
        print(f"    실제와 겹친 종목: {hit}")
        miss=[t for t in act.index if t not in sw.index]
        print(f"    실제엔 있으나 shadow에 없음: {miss}")
compare("NANC", NANC_act, "D")
compare("GOP", GOP_act, "R")
