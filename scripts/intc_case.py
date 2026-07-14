#!/usr/bin/env python3
"""인텔(INTC) 케이스 — 의원 매수 시작시점·누적규모·장기 성과.
하원: 캐시 PDF 재파싱(금액 포함), 상원: senate_ptr_transactions.csv(금액 보유).
성과 horizon: +126/+252/+504 거래일 + 현재까지. 금액은 신고구간 중간값(근사)."""
import os, re, csv, subprocess, zipfile
import xml.etree.ElementTree as ET
import numpy as np, pandas as pd, yfinance as yf
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data"); CACHE=os.path.join(DATA,"ptr_cache")
TARGET="INTC"
ANCHOR=re.compile(r'\b([PSE])\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})')
TAG=re.compile(r'\[([A-Z]{2})\]'); TICK=re.compile(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$')
AMT=re.compile(r'\$([\d,]+)\s*-\s*\$([\d,]+)')
SUFFIX={"jr","sr","ii","iii","iv","v"}
ROSTER={}
for fn in ["legislators-current.csv","legislators-historical.csv"]:
    for r in csv.DictReader(open(os.path.join("/tmp",fn))):
        ROSTER.setdefault(r["last_name"].strip().lower(), r["party"][:1].upper())
def party_last(member):
    toks=[t.strip(".,") for t in member.replace(","," ").split()]
    toks=[t for t in toks if t.lower() not in SUFFIX]
    p=ROSTER.get(toks[-1].lower(),"?") if toks else "?"
    return "D" if p=="I" else p
def mid(s):
    m=AMT.search(str(s));  return (int(m.group(1).replace(",",""))+int(m.group(2).replace(",","")))/2 if m else np.nan

rows=[]
# ---- 하원 PDF 재파싱 (INTC만) ----
for y in ["2024","2025","2026"]:
    zp=os.path.join(CACHE,f"{y}FD.zip")
    if not os.path.exists(zp): continue
    root=ET.fromstring(zipfile.ZipFile(zp).read(f"{y}FD.xml"))
    for mem in root:
        if mem.findtext("FilingType")!="P": continue
        doc=(mem.findtext("DocID") or "").strip(); pdf=os.path.join(CACHE,f"{doc}.pdf")
        if not (doc.isdigit() and os.path.exists(pdf)): continue
        member=f'{mem.findtext("First") or ""} {mem.findtext("Last") or ""}'.strip()
        sd=(mem.findtext("StateDst") or "");
        try: txt=subprocess.run(["pdftotext","-layout",pdf,"-"],capture_output=True,text=True,timeout=20).stdout
        except Exception: continue
        prev=0
        for t in TAG.finditer(txt):
            chunk=txt[prev:t.end()]; prev=t.end()
            if t.group(1)!="ST": continue
            a=ANCHOR.search(chunk)
            if not a: continue
            cands=re.findall(r'\(([A-Za-z0-9.\-]{1,9})\)',chunk)
            tk=next((c for c in reversed(cands) if TICK.match(c)),None)
            if tk!=TARGET: continue
            am=AMT.search(chunk[a.end():])
            usd=(int(am.group(1).replace(",",""))+int(am.group(2).replace(",","")))/2 if am else np.nan
            rows.append(dict(chamber="House",member=member,party=party_last(member),
                             type=a.group(1),transaction_date=a.group(2),filing_date=mem.findtext("FilingDate"),usd=usd))
# ---- 상원 CSV (INTC만) ----
sen=pd.read_csv(os.path.join(DATA,"senate_ptr_transactions.csv"))
sen=sen[sen.ticker==TARGET]
for _,r in sen.iterrows():
    rows.append(dict(chamber="Senate",member=r["member"],party=party_last(r["member"]),
                     type=r["type"],transaction_date=r["transaction_date"],filing_date=r["filing_date"],usd=mid(r["amount"])))
df=pd.DataFrame(rows)
df["transaction_date"]=pd.to_datetime(df["transaction_date"],errors="coerce")
df=df.dropna(subset=["transaction_date"]).sort_values("transaction_date")
df=df[(df.transaction_date>="2023-06-01")&(df.transaction_date<="2026-05-22")]
buys=df[df.type=="P"]; sells=df[df.type=="S"]

print("="*64); print(f"[{TARGET}] 의원 거래 개요"); print("="*64)
print(f"총 거래 {len(df)} (매수 {len(buys)}, 매도 {len(sells)}) | 거래위원 {df.member.nunique()}명")
print(f"정당: {df.party.value_counts().to_dict()}")
print(f"첫 매수: {buys.transaction_date.min().date()} | 최근 매수: {buys.transaction_date.max().date()}")
print(f"누적 매수금액(중간값 추정): ${buys.usd.sum():,.0f} | 매도 ${sells.usd.sum():,.0f} | 순매수 ${buys.usd.sum()-sells.usd.sum():,.0f}")

print("\n── 분기별 매수 (건수 / 누적금액) ──")
buys2=buys.copy(); buys2["q"]=buys2.transaction_date.dt.to_period("Q").astype(str)
qg=buys2.groupby("q").agg(건수=("usd","size"),금액=("usd","sum"))
qg["누적금액"]=qg["금액"].cumsum()
print(qg.assign(금액=qg.금액.map(lambda x:f"${x:,.0f}"),누적금액=qg.누적금액.map(lambda x:f"${x:,.0f}")).to_string())

print("\n── 매수 상위 위원 (금액) ──")
top=buys.groupby(["member","party"]).agg(건수=("usd","size"),금액=("usd","sum")).sort_values("금액",ascending=False).head(8)
print(top.assign(금액=top.금액.map(lambda x:f"${x:,.0f}")).to_string())

# ---- 주가 성과 (장기 horizon) ----
px=yf.download([TARGET,"SPY"],start="2023-06-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"].dropna()
idx=px.index
print("\n── INTC 주가 (조정) ──")
for d in ["2024-01-02","2024-08-01","2024-09-10","2025-01-17","2025-08-01","2026-05-22"]:
    sub=px[px.index<=pd.Timestamp(d)]
    if len(sub): print(f"  {sub.index[-1].date()}: INTC ${sub[TARGET].iloc[-1]:.2f}")
lo=px[TARGET].idxmin(); print(f"  최저점: {lo.date()} ${px[TARGET].min():.2f}  → 현재 ${px[TARGET].iloc[-1]:.2f} ({(px[TARGET].iloc[-1]/px[TARGET].min()-1)*100:+.0f}%)")

def fret(d,h):
    pos=idx.searchsorted(pd.Timestamp(d))
    if pos>=len(idx): return None,None
    end=min(pos+h,len(idx)-1) if h else len(idx)-1
    if pos>=end: return None,None
    r=(px[TARGET].iloc[end]/px[TARGET].iloc[pos]-1)*100
    ex=r-(px["SPY"].iloc[end]/px["SPY"].iloc[pos]-1)*100
    return r,ex
print("\n── 매수 성과: horizon별 평균 (의원 매수일 기준) ──")
print(f"{'horizon':<14}{'평균INTC수익%':>14}{'평균초과%':>12}{'표본':>6}")
for label,h in [("+126일(~6M)",126),("+252일(~1Y)",252),("+504일(~2Y)",504),("현재까지",None)]:
    rs=[fret(d,h) for d in buys.transaction_date]
    rr=[x[0] for x in rs if x[0] is not None]; ee=[x[1] for x in rs if x[1] is not None]
    if rr: print(f"{label:<14}{np.mean(rr):>+14.1f}{np.mean(ee):>+12.1f}{len(rr):>6}")
print("\n금액가중 '현재까지' 평균수익:",
      f"{np.average([fret(d,None)[0] for d in buys.transaction_date if fret(d,None)[0] is not None], weights=[u for u,d in zip(buys.usd,buys.transaction_date) if fret(d,None)[0] is not None]):+.1f}%")
