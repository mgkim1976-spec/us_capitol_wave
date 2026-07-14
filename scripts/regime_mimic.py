#!/usr/bin/env python3
"""4정권 regime 검정 — ETF 이전까지 모방포트 재구성. '여당 모방포트 우위'가 반복되나(시스템) vs AI우연(n=1)?
각 정권 시작시점에 각 당의 시가가중 모방포트(누적 순매수→주식수 환산, 거래일 가격)를 구성→정권기간 수익 vs SPY·상대당.
한계: 상장폐지 종목 제외(생존편향, 상방), 금액=구간중간값, 위원회/정보 아닌 *거래기반* 모방."""
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
# 결합
h=pd.read_csv(os.path.join(DATA,"congress_ptr_transactions.csv"),parse_dates=["transaction_date"]); h["amt"]=pd.to_numeric(h["amount"],errors="coerce")
s=pd.read_csv(os.path.join(DATA,"senate_ptr_transactions.csv"),parse_dates=["transaction_date"]); s["amt"]=s["amount"].map(mid)
d=pd.concat([h[["member","ticker","type","transaction_date","amt"]],s[["member","ticker","type","transaction_date","amt"]]],ignore_index=True)
d["party"]=d.member.map(party); d=d.dropna(subset=["amt","transaction_date"]); d=d[d.amt>0]
d=d[d.ticker.str.match(r'^[A-Z]{1,5}$',na=False)]
print(f"결합 거래(금액有): {len(d)} ({d.transaction_date.min().date()}~{d.transaction_date.max().date()}) | D {(d.party=='D').sum()} R {(d.party=='R').sum()}")
# 가격 패널 (상위 거래종목)
UNIV=d.groupby("ticker").amt.sum().sort_values(ascending=False).head(300).index.tolist()
px=yf.download([t for t in UNIV]+["SPY"],start="2012-06-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
def pat(tk,dt):
    if tk not in px: return None
    sx=px[tk].dropna(); sx=sx[sx.index<=pd.Timestamp(dt)]
    return sx.iloc[-1] if len(sx) else None
REG=[("오바마2기(D)","2013-01-20","2017-01-20","D"),("트럼프1기(R)","2017-01-20","2021-01-20","R"),
     ("바이든(D)","2021-01-20","2025-01-20","D"),("트럼프2기(R)","2025-01-20","2026-05-22","R")]
def port_ret(pty,start,end):
    sub=d[(d.party==pty)&(d.transaction_date<pd.Timestamp(start))&(d.transaction_date>=pd.Timestamp(start)-pd.Timedelta(days=1095))]  # 직전 3년
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
    dR,_=port_ret("D",a,b); rR,_=port_ret("R",a,b)
    rule=dR if ruling=="D" else rR; other=rR if ruling=="D" else dR
    rows.append(dict(정권=name,여당=ruling,D포트=dR,R포트=rR,SPY=spy,여당포트=rule,
                     여당vsSPY=(rule-spy) if rule is not None else None,여당vs상대=(rule-other) if rule and other else None))
r=pd.DataFrame(rows)
pd.set_option("display.width",140)
print("\n=== 4정권 모방포트 수익률 (각 정권시작 시가가중 보유, 정권말까지) ===")
print(r.round(0).to_string(index=False))
w_spy=(r.여당vsSPY>0).sum(); w_oth=(r.여당vs상대>0).sum()
print(f"\n여당포트가 SPY 상회: {w_spy}/4 정권 | 상대당 상회: {w_oth}/4 정권")
print("→ 4/4 반복이면 시스템 인센티브 지지. AI국면(바이든·트럼프2)만이면 우연.")
r.to_csv(os.path.join(DATA,"regime_mimic.csv"),index=False)
