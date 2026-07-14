#!/usr/bin/env python3
"""위원별 투자성과 리더보드 + 최근 매수·매도(수익실현) 시계열.
데이터: data/congress_ptr_transactions.csv (하원 PTR 2024-2026)
성과: 각 매수의 거래일 기준 +126거래일 SPY대비 초과수익(고정기간=비교가능). N>=15만 순위.
한계: 하원만·등가중·포지션크기/매도 무시·표본 짧음 → 서술적이며 예측 아님."""
import os, numpy as np, pandas as pd, yfinance as yf
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
PXFILE=os.path.join(DATA,"ptr_prices.csv")
df=pd.read_csv(os.path.join(DATA,"congress_ptr_transactions.csv"),
               parse_dates=["transaction_date","filing_date"])
print("데이터 기간:", df.transaction_date.min().date(),"~",df.transaction_date.max().date(),"| 거래",len(df))
buys=df[df.type=="P"].copy(); sells=df[df.type=="S"].copy()

# ---- 가격 패널 최신화 (누락 매수티커 보충) ----
px=pd.read_csv(PXFILE,index_col=0,parse_dates=True) if os.path.exists(PXFILE) else pd.DataFrame()
ymap={t:t.replace(".","-") for t in buys.ticker.unique()}
need=sorted(set(ymap.values())|{"SPY"} - set(px.columns))
if need:
    print(f"가격 추가 다운로드: {len(need)}개")
    for i in range(0,len(need),120):
        d=yf.download(need[i:i+120],start="2023-09-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
        px=pd.concat([px,d],axis=1)
    px=px.loc[:,~px.columns.duplicated()]; px.to_csv(PXFILE)
idx=px.index; SPY=px["SPY"]

def fwd_excess(ticker,date,h=126):
    yt=ticker.replace(".","-")
    if yt not in px.columns: return None
    pos=idx.searchsorted(pd.Timestamp(date)); t1=pos+h
    if pos>=len(idx) or t1>=len(idx): return None
    s=px[yt]; p0=s.iloc[pos]; p1=s.iloc[t1]
    if pd.isna(p0) or pd.isna(p1) or p0<=0: return None
    return ((p1/p0-1)-(SPY.iloc[t1]/SPY.iloc[pos]-1))*100

# ================= 1) 위원 성과 리더보드 =================
buys["exc126"]=[fwd_excess(t,d) for t,d in zip(buys.ticker,buys.transaction_date)]
ev=buys.dropna(subset=["exc126"])
g=ev.groupby(["member","party"])["exc126"].agg(["count","mean","median"])
g["hit"]=ev.groupby(["member","party"])["exc126"].apply(lambda s:(s>0).mean()*100).values
g=g[g["count"]>=15].sort_values("mean",ascending=False).round(1)
print(f"\n{'='*70}\n[1] 위원별 매수 성과 (거래일+126거래일, SPY대비 초과%, N>=15)\n{'='*70}")
print("── 상위 12 ──")
print(g.head(12).to_string())
print("\n── 하위 8 ──")
print(g.tail(8).to_string())
print(f"\n평가대상 위원수(N>=15): {len(g)} | 전체 매수 평균초과수익: {ev.exc126.mean():+.2f}% (승률 {(ev.exc126>0).mean()*100:.0f}%)")

# ================= 2) 최근 매수 시계열 =================
print(f"\n{'='*70}\n[2] 최근 매수 시계열 (거래일 기준)\n{'='*70}")
buys["ym"]=buys.transaction_date.dt.to_period("M").astype(str)
piv=buys.groupby(["ym","party"]).size().unstack(fill_value=0).tail(8)
print("월별 매수 건수 (D / R):")
print(piv.to_string())
recent=buys[buys.transaction_date>=buys.transaction_date.max()-pd.Timedelta(days=120)]
print(f"\n최근 120일({recent.transaction_date.min().date()}~) 최다 매수:")
for p in ["D","R"]:
    top=recent[recent.party==p].ticker.value_counts().head(10)
    print(f"  {p}: "+", ".join(f"{t}({c})" for t,c in top.items()))

# ================= 3) 최근 매도(수익실현) 시계열 =================
print(f"\n{'='*70}\n[3] 최근 매도/수익실현 시계열\n{'='*70}")
sells["ym"]=sells.transaction_date.dt.to_period("M").astype(str)
pivs=sells.groupby(["ym","party"]).size().unstack(fill_value=0).tail(8)
print("월별 매도 건수 (D / R):")
print(pivs.to_string())
recents=sells[sells.transaction_date>=sells.transaction_date.max()-pd.Timedelta(days=120)]
print(f"\n최근 120일({recents.transaction_date.min().date()}~) 최다 매도(수익실현):")
for p in ["D","R"]:
    top=recents[recents.party==p].ticker.value_counts().head(10)
    print(f"  {p}: "+", ".join(f"{t}({c})" for t,c in top.items()))
# 순매수 신호(최근 120일, 건수 기준 매수-매도)
print("\n최근 120일 순매수 상위(매수-매도 건수, 전체):")
nb=recent.ticker.value_counts().subtract(recents.ticker.value_counts(),fill_value=0).sort_values(ascending=False)
print("  순매수+: "+", ".join(f"{t}(+{int(v)})" for t,v in nb.head(10).items()))
print("  순매도-: "+", ".join(f"{t}({int(v)})" for t,v in nb.tail(8).items()))
