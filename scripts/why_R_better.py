#!/usr/bin/env python3
"""'왜 R만 성과가 좋아 보이나' 검증 — 당파 실력 vs 베이스레이트(거래량) vs AI베타 vs 상·하원.
지표: 거래일+126거래일 SPY대비 초과수익. 통합 데이터(상·하원)."""
import os, numpy as np, pandas as pd
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
df=pd.read_csv(os.path.join(DATA,"combined_ptr_transactions.csv"),parse_dates=["transaction_date","filing_date"])
px=pd.read_csv(os.path.join(DATA,"ptr_prices.csv"),index_col=0,parse_dates=True); idx=px.index; SPY=px["SPY"]
def fwd(t,d,h=126):
    yt=t.replace(".","-")
    if yt not in px.columns: return None
    pos=idx.searchsorted(pd.Timestamp(d)); t1=pos+h
    if pos>=len(idx) or t1>=len(idx): return None
    p0=px[yt].iloc[pos]; p1=px[yt].iloc[t1]
    if pd.isna(p0) or pd.isna(p1) or p0<=0: return None
    return ((p1/p0-1)-(SPY.iloc[t1]/SPY.iloc[pos]-1))*100
b=df[(df.type=="P")&(df.party.isin(["D","R"]))].copy()
b["exc"]=[fwd(t,d) for t,d in zip(b.ticker,b.transaction_date)]
b=b.dropna(subset=["exc"])

print("="*64); print("[1] 모집단 평균 — 정당 전체 매수 (리더보드 아닌 전수)"); print("="*64)
print(f"{'':4}{'거래수':>8}{'위원수':>7}{'평균초과%':>10}{'중위%':>8}{'승률%':>8}")
for p in ["D","R"]:
    s=b[b.party==p]
    print(f"{p:4}{len(s):>8}{s.member.nunique():>7}{s.exc.mean():>+10.2f}{s.exc.median():>+8.2f}{(s.exc>0).mean()*100:>8.1f}")
print("→ 모집단 평균이 비슷하면 'R 우위'는 리더보드 착시(거래량 차이)")

print("\n"+"="*64); print("[2] 거래 빈도 — R이 더 많이 사나? (베이스레이트)"); print("="*64)
for ch in ["House","Senate"]:
    sub=df[(df.chamber==ch)&(df.type=="P")]
    vc=sub.party.value_counts()
    print(f"  {ch}: 매수 D {vc.get('D',0)} / R {vc.get('R',0)}  | 거래위원 D {sub[sub.party=='D'].member.nunique()} / R {sub[sub.party=='R'].member.nunique()}")

print("\n"+"="*64); print("[3] 체임버 × 정당 성과"); print("="*64)
print(f"{'그룹':14}{'거래':>7}{'위원':>6}{'평균초과%':>10}{'승률%':>8}")
for ch in ["House","Senate"]:
    for p in ["D","R"]:
        s=b[(b.chamber==ch)&(b.party==p)]
        if len(s)<10: continue
        print(f"{ch+'-'+p:14}{len(s):>7}{s.member.nunique():>6}{s.exc.mean():>+10.2f}{(s.exc>0).mean()*100:>8.1f}")

print("\n"+"="*64); print("[4] 리더보드 구성 — 착시 검증 (N>=20 위원)"); print("="*64)
g=b.groupby(["member","party"])["exc"].agg(["count","mean"]); g=g[g["count"]>=20]
print(f"  N>=20 위원수: D {len(g[g.index.get_level_values('party')=='D'])} / R {len(g[g.index.get_level_values('party')=='R'])}")
print("  → R이 활발 트레이더가 많아 상·하위 슬롯 모두 R이 채움(상위도 하위도 R)")
print("  위원평균(equal-weight, 각 위원 1표):")
for p in ["D","R"]:
    mm=g[g.index.get_level_values('party')==p]["mean"]
    print(f"    {p}: 위원별 평균초과의 평균 {mm.mean():+.2f}% (median {mm.median():+.2f}%, n={len(mm)})")

print("\n"+"="*64); print("[5] AI 베타가 진짜 동력인가 — 정당별 AI종목 매수비중 & AI/비AI 성과"); print("="*64)
AI={"NVDA","AMD","AVGO","SMCI","TSM","ASML","LRCX","AMAT","MU","ANET","DELL","MSFT","GOOG","GOOGL",
    "AMZN","META","AAPL","PLTR","TSLA","NFLX","CRM","ORCL","INTC","QCOM","MRVL","ARM","NOW","PANW","CRWD"}
b["isAI"]=b.ticker.isin(AI)
for p in ["D","R"]:
    s=b[b.party==p]
    print(f"  {p}: AI종목 매수비중 {s.isAI.mean()*100:.0f}%  | AI매수 평균초과 {s[s.isAI].exc.mean():+.1f}%  비AI {s[~s.isAI].exc.mean():+.1f}%")
print(f"\n  전체: AI매수 평균초과 {b[b.isAI].exc.mean():+.1f}% vs 비AI {b[~b.isAI].exc.mean():+.1f}%  (AI가 동력이면 격차 큼)")
