#!/usr/bin/env python3
"""2019~ 의원(상·하원) 매매 종합:
A) 종목별 누적 순매수금액 + 성과
B) 집계 net-flow(매수$-매도$) 시계열 = 의원 전체 '주식 익스포저' 증감
C) net-flow가 시장 타이밍 시그널인가 (SPY 선행/동행 검증, 코로나·약세장)
금액=신고구간 중간값(근사). 거래일 기준(=실제 행동), 필링지연으로 실시간 신호 아님은 별도 명시."""
import os, re, csv, numpy as np, pandas as pd, yfinance as yf
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
SUFFIX={"jr","sr","ii","iii","iv","v"}
ROSTER={}
for fn in ["legislators-current.csv","legislators-historical.csv"]:
    for r in csv.DictReader(open(os.path.join("/tmp",fn))):
        ROSTER.setdefault(r["last_name"].strip().lower(), r["party"][:1].upper())
def remap(member):
    toks=[t.strip(".,") for t in str(member).replace(","," ").split()]
    toks=[t for t in toks if t.lower() not in SUFFIX]
    p=ROSTER.get(toks[-1].lower(),"?") if toks else "?"
    return "D" if p=="I" else p
def mid(s):
    m=re.search(r'\$([\d,]+)\s*-\s*\$([\d,]+)',str(s))
    return (int(m.group(1).replace(",",""))+int(m.group(2).replace(",","")))/2 if m else np.nan

# ---- combine ----
h=pd.read_csv(os.path.join(DATA,"congress_ptr_transactions.csv"),parse_dates=["transaction_date","filing_date"])
h["amount"]=pd.to_numeric(h["amount"],errors="coerce")
s=pd.read_csv(os.path.join(DATA,"senate_ptr_transactions.csv"),parse_dates=["transaction_date","filing_date"])
s["amount"]=s["amount"].map(mid)
for d in (h,s):
    if "chamber" not in d: d["chamber"]="?"
cols=["member","chamber","ticker","type","transaction_date","filing_date","amount"]
df=pd.concat([h[cols],s[cols]],ignore_index=True)
df["party"]=df.member.map(remap)
df["signed"]=np.where(df.type=="P",df.amount,np.where(df.type=="S",-df.amount,0))
df=df.dropna(subset=["transaction_date"])
df=df[(df.transaction_date>="2019-01-01")]
print(f"통합 거래 {len(df)} ({df.transaction_date.min().date()}~{df.transaction_date.max().date()}) "
      f"| 하원 {(df.chamber=='House').sum()} 상원 {(df.chamber=='Senate').sum()} | 금액유효 {df.amount.notna().mean()*100:.0f}%")

# ================= A) 종목별 누적 =================
print("\n"+"="*70); print("[A] 종목별 누적 순매수금액 TOP20 (2019~, 중간값 추정)"); print("="*70)
g=df.groupby("ticker").agg(순매수=("signed","sum"),
        매수액=("amount",lambda x: df.loc[x.index][df.loc[x.index].type=="P"].amount.sum()),
        거래수=("ticker","size"), 위원수=("member","nunique"),
        첫매수=("transaction_date","min")).sort_values("순매수",ascending=False)
top=g.head(20)
print(top.assign(순매수=top.순매수.map(lambda x:f"${x/1e6:.1f}M"),
                 매수액=top.매수액.map(lambda x:f"${x/1e6:.1f}M"),
                 첫매수=top.첫매수.dt.date).to_string())

# 성과(상위 종목): 거래일 가중평균 → 현재
tickers=list(top.index)+["SPY"]
ymap={t:t.replace(".","-") for t in tickers}
px=yf.download(sorted(set(ymap.values())),start="2019-01-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
SPY=px["SPY"]; last=px.index[-1]
print("\n── 상위 누적 종목의 성과 (매수액가중평균 매수일 → 현재) ──")
print(f"{'티커':<7}{'가중매수일':>12}{'수익%':>9}{'SPY초과%':>10}")
for t in top.index[:15]:
    sub=df[(df.ticker==t)&(df.type=="P")&df.amount.notna()]
    if sub.amount.sum()<=0: continue
    wdate=pd.Timestamp(np.average(sub.transaction_date.view("int64"),weights=sub.amount))
    yt=ymap[t]
    if yt not in px.columns: continue
    ser=px[yt].dropna(); pos=ser.index.searchsorted(wdate)
    if pos>=len(ser): continue
    r=(ser.iloc[-1]/ser.iloc[pos]-1)*100
    sp=(SPY.iloc[-1]/SPY.loc[:wdate].iloc[-1]-1)*100 if len(SPY.loc[:wdate]) else np.nan
    print(f"{t:<7}{str(wdate.date()):>12}{r:>+9.0f}{r-sp:>+10.0f}")

# ================= B) net-flow 시계열 (익스포저 증감) =================
print("\n"+"="*70); print("[B] 분기별 집계 net-flow & 매도비중 (의원 전체 익스포저)"); print("="*70)
df["q"]=df.transaction_date.dt.to_period("Q").astype(str)
q=df.groupby("q").apply(lambda x: pd.Series({
    "매수$M":x[x.type=="P"].amount.sum()/1e6,
    "매도$M":x[x.type=="S"].amount.sum()/1e6,
    "순매수$M":x.signed.sum()/1e6,
    "매도비중%":100*(x.type=="S").sum()/max((x.type.isin(["P","S"])).sum(),1),
    "거래수":len(x)}),include_groups=False).round(1)
# SPY 분기수익
spq=SPY.resample("QE").last().pct_change()*100; spq.index=spq.index.to_period("Q").astype(str)
q["SPY분기%"]=q.index.map(spq.round(1))
print(q.to_string())

# ================= C) 타이밍 시그널 검증 =================
print("\n"+"="*70); print("[C] net-flow가 시장 타이밍 시그널인가"); print("="*70)
qq=q.copy(); qq["SPY_next"]=qq["SPY분기%"].shift(-1)
v=qq.dropna(subset=["순매수$M","SPY_next"])
print(f"순매수$ ↔ 다음분기 SPY 상관: {v['순매수$M'].corr(v['SPY_next']):+.2f}")
print(f"매도비중% ↔ 다음분기 SPY 상관: {v['매도비중%'].corr(v['SPY_next']):+.2f}  (음(-)이면 매도多→하락 선행)")
print("\n매도비중 최고 분기 (위험회피 신호 후보):")
print(qq.sort_values("매도비중%",ascending=False)[["매도비중%","순매수$M","SPY분기%","SPY_next"]].head(6).to_string())
print("\n순매수 최저(=순매도) 분기:")
print(qq.sort_values("순매수$M").head(6)[["순매수$M","매도비중%","SPY분기%","SPY_next"]].to_string())
df.to_csv(os.path.join(DATA,"combined_2019_2026.csv"),index=False)
print("\n저장: data/combined_2019_2026.csv")
