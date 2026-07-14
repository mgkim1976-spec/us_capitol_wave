#!/usr/bin/env python3
"""ETF 복제 가능성 검증 — 공개 PTR로 'shadow NANC/GOP'를 재구성해 실제 보유와 비교.
운용사 방법론(정당 투입 '총금액' 가중, 상·하원, 매수·매도 반영)을 하원 데이터로 모사.
금액은 PTR의 구간(예 $15,001-$50,000) 중간값 사용 — ETF도 같은 구간정보만 가짐.
한계: 하원만(상원 eFD 미포함), 캐시 PDF 재파싱."""
import os, re, csv, subprocess, zipfile
import xml.etree.ElementTree as ET
import pandas as pd
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA=os.path.join(HERE,"data"); CACHE=os.path.join(DATA,"ptr_cache")
TICKER_RE=re.compile(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$')
ANCHOR=re.compile(r'\b([PSE])\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})')
TAG=re.compile(r'\[([A-Z]{2})\]')
AMT=re.compile(r'\$([\d,]+)\s*-\s*\$([\d,]+)')

# party map (reuse roster in /tmp)
def load_party():
    nd={}; sd={}
    for fn in ["legislators-current.csv","legislators-historical.csv"]:
        for r in csv.DictReader(open(os.path.join("/tmp",fn))):
            p=r["party"][:1].upper() if r["party"] else "?"
            nd.setdefault((r["last_name"].strip().lower(),r["state"]),p)
            if r["type"]=="rep" and r["district"]:
                sd.setdefault((r["state"],r["district"].zfill(2)),p)
    return nd,sd
ND,SD=load_party()
def party_of(last,state,dist):
    if dist and (state,dist.zfill(2)) in SD: return SD[(state,dist.zfill(2))]
    return ND.get((last.strip().lower(),state),"?")

def parse_amounts(path):
    txt=subprocess.run(["pdftotext","-layout",path,"-"],capture_output=True,text=True,timeout=30).stdout
    out=[]; prev=0
    for t in TAG.finditer(txt):
        chunk=txt[prev:t.end()]; prev=t.end()
        if t.group(1)!="ST": continue
        a=ANCHOR.search(chunk)
        if not a: continue
        typ=a.group(1)
        cands=re.findall(r'\(([A-Za-z0-9.\-]{1,9})\)',chunk)
        tk=next((c for c in reversed(cands) if TICKER_RE.match(c)),None)
        if not tk: continue
        am=AMT.search(chunk[a.end():])
        if am:
            lo=int(am.group(1).replace(",","")); hi=int(am.group(2).replace(",",""))
            mid=(lo+hi)/2
        else: mid=0
        out.append((typ,tk,mid))
    return out

# rebuild transactions with $ from cached PDFs
rows=[]
for y in ["2024","2025"]:
    root=ET.fromstring(zipfile.ZipFile(os.path.join(CACHE,f"{y}FD.zip")).read(f"{y}FD.xml"))
    for mem in root:
        if mem.findtext("FilingType")!="P": continue
        doc=(mem.findtext("DocID") or "").strip()
        pdf=os.path.join(CACHE,f"{doc}.pdf")
        if not (doc.isdigit() and os.path.exists(pdf)): continue
        sd=(mem.findtext("StateDst") or "").strip(); st=sd[:2]; dist=sd[2:]
        party=party_of(mem.findtext("Last") or "", st, dist)
        try: txs=parse_amounts(pdf)
        except Exception: continue
        for typ,tk,mid in txs:
            rows.append(dict(party=party,ticker=tk,type=typ,usd=mid))
df=pd.DataFrame(rows)
df["signed"]=df.apply(lambda r: r.usd if r.type=="P" else (-r.usd if r.type=="S" else 0), axis=1)

def shadow(party, cap=8.0, top=150):
    """운용사 규칙 근사: 정당 순매수금액 가중 + 단일종목 캡 + 종목수 제한."""
    sub=df[df.party==party]
    net=sub.groupby("ticker")["signed"].sum()
    net=net[net>0].sort_values(ascending=False).head(top)
    w=net/net.sum()*100
    # 단일종목 캡 반복 재분배
    for _ in range(50):
        over=w>cap
        if not over.any(): break
        excess=(w[over]-cap).sum(); w[over]=cap
        room=w[~over]; w[~over]=room+excess*room/room.sum()
    return w.round(2)

ACTUAL={
 "NANC":{"NVDA":10.6,"GOOG":7.3,"MSFT":5.9,"AMZN":5.6,"AAPL":4.0,"AMAT":3.8,"NFLX":3.1,"PM":2.9,"AXP":2.8,"COST":2.6},
 "GOP":{"FIX":8.8,"INTC":6.6,"JPM":4.1,"IBIT":3.7,"ANET":3.3,"NVDA":3.2,"UTHR":2.3,"T":2.0,"AMD":2.0,"ALL":1.9},
}
MAP={"NANC":"D","GOP":"R"}
for etf,party in MAP.items():
    sw=shadow(party)
    print("="*64)
    print(f"[{etf}] shadow(하원 금액가중) top15  vs  실제 보유 top10")
    top=sw.head(15)
    print("  shadow:", ", ".join(f"{t} {v}%" for t,v in top.items()))
    act=ACTUAL[etf]
    hit=[t for t in act if t in sw.index]
    hit_top30=[t for t in act if t in sw.head(30).index]
    print(f"  실제 top10 중 shadow에 존재: {len(hit)}/10 {hit}")
    print(f"  실제 top10 중 shadow top30 내: {len(hit_top30)}/10")
    # 비중상관 (겹치는 종목)
    if len(hit)>=3:
        import numpy as np
        a=np.array([act[t] for t in hit]); b=np.array([sw[t] for t in hit])
        print(f"  겹친 {len(hit)}종목 비중상관: {np.corrcoef(a,b)[0,1]:+.2f}")
    print(f"  shadow 종목수: {len(sw)}")
print("\n해석: 하원만으로도 실제 대형보유 상당수 복제. 미스매치 원인=상원 미포함·가중·리밸런싱 시차.")
