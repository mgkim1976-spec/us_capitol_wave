#!/usr/bin/env python3
"""분석: 신고 추종 이벤트 스터디 — '정보우위 잔존' 검증.
의원 매수신고에 대해 ⒜ 거래일 기준(이론적 최대) ⒝ 공개신고일 기준(실제 추종가능) 으로
+21/+63/+126 거래일 SPY대비 초과수익을 정당별 측정. ⒝가 양(+)이면 지연신고를 따라 사도 알파 잔존."""
import os, numpy as np, pandas as pd, yfinance as yf
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
PXFILE=os.path.join(DATA,"ptr_prices.csv")
df=pd.read_csv(os.path.join(DATA,"congress_ptr_transactions.csv"),
               parse_dates=["transaction_date","filing_date"])
buys=df[df.type=="P"].copy()
tickers=sorted(buys.ticker.unique())
ymap={t:t.replace(".","-") for t in tickers}      # yfinance class-share format

# ---- price panel (cache) ----
if os.path.exists(PXFILE):
    px=pd.read_csv(PXFILE,index_col=0,parse_dates=True)
else:
    ylist=sorted(set(ymap.values()))+["SPY"]
    frames=[]
    for i in range(0,len(ylist),120):
        batch=ylist[i:i+120]
        d=yf.download(batch,start="2023-09-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
        frames.append(d); print(f"  downloaded {i+len(batch)}/{len(ylist)}")
    px=pd.concat(frames,axis=1)
    px=px.loc[:,~px.columns.duplicated()]
    px.to_csv(PXFILE)
print("price panel:",px.shape,"date",px.index.min().date(),"→",px.index.max().date())
idx=px.index; SPY=px["SPY"]

def fwd_excess(ticker,event_date,h):
    yt=ymap.get(ticker,ticker)
    if yt not in px.columns: return None
    s=px[yt]
    pos=idx.searchsorted(pd.Timestamp(event_date))   # first >= event
    if pos>=len(idx): return None
    t0=pos
    t1=t0+h
    if t1>=len(idx): return None
    p0=s.iloc[t0]; p1=s.iloc[t1]
    if pd.isna(p0) or pd.isna(p1) or p0<=0: return None
    r=(p1/p0-1)
    rs=(SPY.iloc[t1]/SPY.iloc[t0]-1)
    return (r-rs)*100

HOR={"+21일(~1M)":21,"+63일(~3M)":63,"+126일(~6M)":126}
def run(anchor_col,label):
    print(f"\n===== 기준: {label} =====")
    print(f"{'창':<14}{'정당':<5}{'N':>6}{'평균초과%':>10}{'중위%':>8}{'승률%':>8}{'t값':>7}")
    for hl,h in HOR.items():
        for p in ["D","R"]:
            sub=buys[buys.party==p]
            vals=[fwd_excess(t,d,h) for t,d in zip(sub.ticker,sub[anchor_col])]
            vals=[v for v in vals if v is not None]
            if len(vals)<20:
                print(f"{hl:<14}{p:<5}{len(vals):>6}  (표본부족)"); continue
            a=np.array(vals); t=a.mean()/(a.std(ddof=1)/np.sqrt(len(a)))
            print(f"{hl:<14}{p:<5}{len(vals):>6}{a.mean():>+10.2f}{np.median(a):>+8.2f}{(a>0).mean()*100:>8.1f}{t:>7.2f}")
        print()

run("transaction_date","거래일 (이론적 최대 — 의원 실제 매수시점)")
run("filing_date","공개신고일 (실제 추종가능 — 펀드/대중 진입시점)")
print("판독: 신고일기준 초과수익이 0 근처/음수면 → 지연신고 추종에 정보우위 없음 (펀드 전략의 한계)")
