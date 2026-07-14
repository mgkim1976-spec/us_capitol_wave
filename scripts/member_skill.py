#!/usr/bin/env python3
"""위원 성과의 '이유'와 '지속성' — 운 vs 실력.
A) 지속성: 2024거래 vs 2025거래 위원별 평균초과수익 상관(둘 다 N>=8). 양쪽 다 좋으면 실력 신호.
B) 원인분해: 상위위원의 매수를 종목단위로 — 집중도(상위1·3종목 기여비중)·적중률·AI메가트렌드 비중.
지표: 거래일+126거래일 SPY대비 초과수익. 한계: 하원·등가중·짧은 표본 → 서술적."""
import os, numpy as np, pandas as pd
from scipy.stats import spearmanr, pearsonr
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
df=pd.read_csv(os.path.join(DATA,"congress_ptr_transactions.csv"),parse_dates=["transaction_date","filing_date"])
px=pd.read_csv(os.path.join(DATA,"ptr_prices.csv"),index_col=0,parse_dates=True)
idx=px.index; SPY=px["SPY"]
def fwd(t,d,h=126):
    yt=t.replace(".","-")
    if yt not in px.columns: return None
    pos=idx.searchsorted(pd.Timestamp(d)); t1=pos+h
    if pos>=len(idx) or t1>=len(idx): return None
    p0=px[yt].iloc[pos]; p1=px[yt].iloc[t1]
    if pd.isna(p0) or pd.isna(p1) or p0<=0: return None
    return ((p1/p0-1)-(SPY.iloc[t1]/SPY.iloc[pos]-1))*100
# 이름 정규화(간단): 'C. Scott Franklin'/'Scott Scott Franklin' 등 중복 완화
def norm(n):
    n=n.replace("C. Scott Franklin","Scott Franklin").replace("Scott Scott Franklin","Scott Franklin")
    return " ".join(n.split())
buys=df[df.type=="P"].copy(); buys["member"]=buys.member.map(norm)
buys["exc"]=[fwd(t,d) for t,d in zip(buys.ticker,buys.transaction_date)]
buys=buys.dropna(subset=["exc"]); buys["yr"]=buys.transaction_date.dt.year

# ===== A) 지속성: 2024 vs 2025 =====
print("="*68); print("[A] 지속성 — 2024거래 vs 2025거래 위원별 평균초과수익"); print("="*68)
def yr_stats(y):
    s=buys[buys.yr==y].groupby("member")["exc"]
    return pd.DataFrame({"mean":s.mean(),"n":s.size()})
a=yr_stats(2024); b=yr_stats(2025)
m=a.join(b,lsuffix="_24",rsuffix="_25").dropna()
m=m[(m.n_24>=8)&(m.n_25>=8)]
print(f"양 기간 N>=8 위원: {len(m)}명")
sp=spearmanr(m["mean_24"],m["mean_25"]); pe=pearsonr(m["mean_24"],m["mean_25"])
print(f"2024↔2025 평균초과 상관: Spearman {sp.statistic:+.2f}(p={sp.pvalue:.2f}) | Pearson {pe.statistic:+.2f}")
print("→ 상관이 0 근처면 '지속성 없음(주로 운)', 양(+)·유의면 '실력 신호'\n")
m["both_pos"]=(m["mean_24"]>0)&(m["mean_25"]>0)
print("두 기간 모두 + (지속적 우수 후보):")
print(m[m.both_pos].sort_values("mean_25",ascending=False)[["mean_24","n_24","mean_25","n_25"]].round(1).to_string())
print("\n두 기간 모두 − (지속적 부진):")
print(m[(m.mean_24<0)&(m.mean_25<0)].sort_values("mean_25")[["mean_24","n_24","mean_25","n_25"]].round(1).head(6).to_string())

# ===== B) 원인분해: 상위 위원 =====
AI={"NVDA","AMD","AVGO","SMCI","TSM","ASML","LRCX","AMAT","MU","ANET","DELL","MSFT","GOOG","GOOGL",
    "AMZN","META","AAPL","PLTR","TSLA","NFLX","CRM","ORCL","INTC","QCOM","MRVL","ARM","NOW","PANW","CRWD"}
full=buys.groupby("member")["exc"].agg(["count","mean"])
top=full[full["count"]>=20].sort_values("mean",ascending=False).head(6).index
print("\n"+"="*68); print("[B] 상위 위원 성과의 '이유' (종목단위 분해, N>=20)"); print("="*68)
for mem in top:
    sub=buys[buys.member==mem]
    tot=sub.exc.sum(); hit=(sub.exc>0).mean()*100
    by=sub.groupby("ticker")["exc"].sum().sort_values(ascending=False)
    top1=by.iloc[0]/tot*100 if tot>0 else 0
    top3=by.head(3).sum()/tot*100 if tot>0 else 0
    ai_share=sub[sub.ticker.isin(AI)].exc.sum()/tot*100 if tot>0 else 0
    winners=", ".join(f"{t}(+{v:.0f})" for t,v in by.head(4).items())
    print(f"\n● {mem}  (N={len(sub)}, 평균초과 {sub.exc.mean():+.1f}%, 적중률 {hit:.0f}%)")
    print(f"   상위1종목 기여 {top1:.0f}% · 상위3 {top3:.0f}% · AI/테크 종목 기여 {ai_share:.0f}%")
    print(f"   주력 승자: {winners}")
print("\n판독: 상위1종목 기여 高 & 적중률 ~50% = 소수 홈런(운). AI비중 高 = 메가트렌드 베타.")
print("      적중률 >>50% & 분산 = 실력 신호. 지속성(A)과 함께 봐야 함.")
