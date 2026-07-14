#!/usr/bin/env python3
"""상·하원 통합 — 지속성 재검증 + 통합 리더보드.
상원 정당 매핑 접미사(Jr./II/IV)·콤마 보정, House+Senate 결합.
King(I)=민주 코커스로 D 편입(표기). 지표: 거래일+126거래일 SPY대비 초과수익."""
import os, csv, numpy as np, pandas as pd, yfinance as yf
from scipy.stats import spearmanr, pearsonr
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")

# ---- 정당 재매핑(접미사 보정) ----
SUFFIX={"jr","sr","ii","iii","iv","v"}
ROSTER={}
for fn in ["legislators-current.csv","legislators-historical.csv"]:
    for r in csv.DictReader(open(os.path.join("/tmp",fn))):
        ROSTER.setdefault(r["last_name"].strip().lower(), r["party"][:1].upper())
def last_of(member):
    last=member.split()[-1] if member else ""
    # member="First M Last, Jr." → 마지막 토큰이 접미사면 그 앞
    toks=[t.strip(".,") for t in member.replace(",", " ").split()]
    toks=[t for t in toks if t.lower() not in SUFFIX]
    return toks[-1].lower() if toks else ""
def remap(member):
    p=ROSTER.get(last_of(member),"?")
    return "D" if p=="I" else p   # King/Sanders(I) → 민주 코커스

# ---- 결합 ----
h=pd.read_csv(os.path.join(DATA,"congress_ptr_transactions.csv"),parse_dates=["transaction_date","filing_date"])
h["chamber"]="House"
s=pd.read_csv(os.path.join(DATA,"senate_ptr_transactions.csv"),parse_dates=["transaction_date","filing_date"])
s["party"]=s.member.map(remap)
cols=["party","member","chamber","ticker","type","transaction_date","filing_date"]
df=pd.concat([h[cols],s[cols]],ignore_index=True)
df.to_csv(os.path.join(DATA,"combined_ptr_transactions.csv"),index=False)
print(f"통합: {len(df)}건 (하원 {len(h)} + 상원 {len(s)}) | 정당 {df.party.value_counts().to_dict()}")
print(f"상원 매핑실패 보정 후: {(s.party=='?').mean()*100:.1f}%")

# ---- 가격 패널 확장 ----
px=pd.read_csv(os.path.join(DATA,"ptr_prices.csv"),index_col=0,parse_dates=True)
buys=df[df.type=="P"].copy()
need=sorted({t.replace(".","-") for t in buys.ticker.unique()} - set(px.columns))
if need:
    print(f"가격 추가 다운로드 {len(need)}개")
    for i in range(0,len(need),120):
        d=yf.download(need[i:i+120],start="2023-09-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
        px=pd.concat([px,d],axis=1)
    px=px.loc[:,~px.columns.duplicated()]; px.to_csv(os.path.join(DATA,"ptr_prices.csv"))
idx=px.index; SPY=px["SPY"]
def fwd(t,d,h=126):
    yt=t.replace(".","-")
    if yt not in px.columns: return None
    pos=idx.searchsorted(pd.Timestamp(d)); t1=pos+h
    if pos>=len(idx) or t1>=len(idx): return None
    p0=px[yt].iloc[pos]; p1=px[yt].iloc[t1]
    if pd.isna(p0) or pd.isna(p1) or p0<=0: return None
    return ((p1/p0-1)-(SPY.iloc[t1]/SPY.iloc[pos]-1))*100
buys["exc"]=[fwd(t,d) for t,d in zip(buys.ticker,buys.transaction_date)]
buys=buys.dropna(subset=["exc"]); buys["yr"]=buys.transaction_date.dt.year

# ---- 지속성 2024 vs 2025 ----
def yr_stats(y):
    s=buys[buys.yr==y].groupby("member")["exc"]; return pd.DataFrame({"mean":s.mean(),"n":s.size()})
a=yr_stats(2024); b=yr_stats(2025)
m=a.join(b,lsuffix="_24",rsuffix="_25").dropna(); m=m[(m.n_24>=8)&(m.n_25>=8)]
print(f"\n{'='*64}\n[지속성] 2024 vs 2025 (상·하원 통합, 양기간 N>=8)\n{'='*64}")
print(f"대상 위원: {len(m)}명 (이전 하원만 8명 → 통합)")
if len(m)>=4:
    sp=spearmanr(m.mean_24,m.mean_25); pe=pearsonr(m.mean_24,m.mean_25)
    print(f"상관: Spearman {sp.statistic:+.2f}(p={sp.pvalue:.2f}) | Pearson {pe.statistic:+.2f}")
print("\n두 해 모두 + (지속 우수):")
print(m[(m.mean_24>0)&(m.mean_25>0)].sort_values("mean_25",ascending=False).round(1).to_string())

# ---- 통합 리더보드 ----
full=buys.groupby(["member","party"])["exc"].agg(["count","mean"])
full["hit"]=buys.groupby(["member","party"])["exc"].apply(lambda s:(s>0).mean()*100).values
full=full[full["count"]>=20].sort_values("mean",ascending=False).round(1)
print(f"\n{'='*64}\n[통합 리더보드] 매수 N>=20, +126일 초과수익\n{'='*64}")
print("── 상위 12 ──"); print(full.head(12).to_string())
print("\n── 하위 6 ──"); print(full.tail(6).to_string())
print(f"\n전체 매수 평균초과 {buys.exc.mean():+.2f}% 승률 {(buys.exc>0).mean()*100:.0f}% | 평가위원 {len(full)}명")
