#!/usr/bin/env python3
"""상원 전용 regime 검정 — 혼합표본 결함(하원 2017이전 스캔본 부재 → 정권간 챔버 커버리지 불일치) 제거.
학술 컨센서스(Ziobrowski 2004: *상원* +12%/년)와 직접 대질하려면 상원만으로 정권 일관 검정이 옳다.
각 정권 시작시점에 상원 D/R 시가가중 모방포트(직전 3년 누적 순매수→주식수, 거래일가)→정권기간 수익 vs SPY·상대당.
한계: 상장폐지 제외(생존편향·상방), 금액=구간중간값, 모방포트는 buy&hold-thru-regime이라 Ziobrowski의 단·중기 이벤트수익과 *직접* 동일검정 아님."""
import os,re,csv,numpy as np,pandas as pd,yfinance as yf
DATA=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"data")
SUF={"jr","sr","ii","iii","iv","v"}
ROST={}
for fn in ["legislators-current.csv","legislators-historical.csv"]:
    p=os.path.join("/tmp",fn)
    if os.path.exists(p):
        for r in csv.DictReader(open(p)): ROST.setdefault(r["last_name"].strip().lower(),r["party"][:1].upper())
def party(member):
    toks=[t.strip(".,") for t in str(member).replace(","," ").split() if t.strip(".,").lower() not in SUF]
    p=ROST.get(toks[-1].lower(),"?") if toks else "?"; return "D" if p=="I" else p
def mid(s):
    if pd.isna(s): return np.nan
    m=re.search(r'\$?([\d,]+)\s*-\s*\$?([\d,]+)',str(s))
    if m: return (int(m.group(1).replace(",",""))+int(m.group(2).replace(",","")))/2
    try: return float(s)
    except: return np.nan
# 상원만
s=pd.read_csv(os.path.join(DATA,"senate_ptr_transactions.csv"),parse_dates=["transaction_date"]); s["amt"]=s["amount"].map(mid)
d=s[["member","ticker","type","transaction_date","amt"]].copy()
d["party"]=d.member.map(party); d=d.dropna(subset=["amt","transaction_date"]); d=d[d.amt>0]
d=d[d.ticker.str.match(r'^[A-Z]{1,5}$',na=False)]
print(f"상원 거래(금액有): {len(d)} ({d.transaction_date.min().date()}~{d.transaction_date.max().date()}) | D {(d.party=='D').sum()} R {(d.party=='R').sum()} ? {(d.party=='?').sum()}")
UNIV=d.groupby("ticker").amt.sum().sort_values(ascending=False).head(300).index.tolist()
px=yf.download([t for t in UNIV]+["SPY"],start="2012-06-01",end="2026-05-27",auto_adjust=True,progress=False)["Close"]
def pat(tk,dt):
    if tk not in px: return None
    sx=px[tk].dropna(); sx=sx[sx.index<=pd.Timestamp(dt)]
    return sx.iloc[-1] if len(sx) else None
REG=[("오바마2기(D)","2013-01-20","2017-01-20","D"),("트럼프1기(R)","2017-01-20","2021-01-20","R"),
     ("바이든(D)","2021-01-20","2025-01-20","D"),("트럼프2기(R)","2025-01-20","2026-05-22","R")]
def port_ret(pty,start,end):
    win=(d.transaction_date<pd.Timestamp(start))&(d.transaction_date>=pd.Timestamp(start)-pd.Timedelta(days=1095))
    sub=d[win] if pty=="ALL" else d[(d.party==pty)&win]
    sh={}
    for _,r in sub.iterrows():
        p0=pat(r.ticker,r.transaction_date)
        if not p0 or p0<=0: continue
        q=r.amt/p0*(1 if r.type=="P" else -1 if r.type=="S" else 0)
        sh[r.ticker]=sh.get(r.ticker,0)+q
    val={}; ret={}
    for tk,q in sh.items():
        if q<=0: continue
        ps,pe=pat(tk,start),pat(tk,end)
        if not ps or not pe or ps<=0: continue
        val[tk]=q*ps; ret[tk]=pe/ps-1
    if not val: return None,0
    tv=sum(val.values()); return sum(val[t]*ret[t] for t in val)/tv*100, len(val)
rows=[]
for name,a,b,ruling in REG:
    spy=(pat("SPY",b)/pat("SPY",a)-1)*100
    dR,dn=port_ret("D",a,b); rR,rn=port_ret("R",a,b); aR,an=port_ret("ALL",a,b)
    rule=dR if ruling=="D" else rR; other=rR if ruling=="D" else dR
    rows.append(dict(정권=name,여당=ruling,D포트=dR,Dn=dn,R포트=rR,Rn=rn,상원전체=aR,SPY=spy,여당포트=rule,
                     상원vsSPY=(aR-spy) if aR is not None else None,
                     여당vsSPY=(rule-spy) if rule is not None else None,여당vs상대=(rule-other) if rule and other else None))
r=pd.DataFrame(rows)
pd.set_option("display.width",160)
print("\n=== 상원 전용 모방포트 수익률 (각 정권시작 시가가중 보유, 정권말까지) ===")
print(r.round(0).to_string(index=False))
w_spy=(r.여당vsSPY>0).sum(); w_oth=(r.여당vs상대>0).sum()
print(f"\n여당포트 SPY 상회: {w_spy} | 상대당 상회: {w_oth} (검정가능 정권 = 데이터有만)")
r.to_csv(os.path.join(DATA,"regime_mimic_senate.csv"),index=False)
