#!/usr/bin/env python3
"""의회(하원) PTR 거래신고 파이프라인 — 공식 House Clerk 데이터 (2019~2026).
XML(신고일·DocID) + PTR PDF(pdftotext 파싱: 티커·거래일·매수매도·**금액구간**) + 정당매핑.
출력: data/congress_ptr_transactions.csv  (amount=구간 중간값 추정, chamber=House).
한계: 하원만, 스캔본/특이서식 누락 가능."""
import os, re, csv, zipfile, urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA=os.path.join(HERE,"data"); CACHE=os.path.join(DATA,"ptr_cache"); os.makedirs(CACHE,exist_ok=True)
UA={"User-Agent":"Mozilla/5.0 (research; congressional disclosure analysis)"}
YEARS=["2013","2014","2015","2016","2017","2018","2019","2020","2021","2022","2023","2024","2025","2026"]
TICKER_RE=re.compile(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$')
ANCHOR=re.compile(r'\b([PSE])\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})')
TAG=re.compile(r'\[([A-Z]{2})\]')
AMT=re.compile(r'\$([\d,]+)\s*-\s*\$([\d,]+)')
import subprocess

def get(url, timeout=40):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()

def load_party():
    m_nd={}; m_sd={}
    for fn in ["legislators-current.csv","legislators-historical.csv"]:
        path=os.path.join("/tmp",fn)
        if not os.path.exists(path):
            open(path,"wb").write(get(f"https://unitedstates.github.io/congress-legislators/{fn}"))
        for r in csv.DictReader(open(path)):
            p=r["party"][:1].upper() if r["party"] else "?"
            ln=r["last_name"].strip().lower(); st=r["state"]
            m_nd.setdefault((ln,st),p)
            if r["type"]=="rep" and r["district"]:
                m_sd.setdefault((st,r["district"].zfill(2)),p)
    return m_nd,m_sd
M_ND,M_SD=load_party()
def party_of(last,state,dist):
    if dist and (state,dist.zfill(2)) in M_SD: return M_SD[(state,dist.zfill(2))]
    p=M_ND.get((last.strip().lower(),state),"?")
    return "D" if p=="I" else p

def filings():
    out=[]
    for y in YEARS:
        zpath=os.path.join(CACHE,f"{y}FD.zip")
        if not os.path.exists(zpath):
            try: open(zpath,"wb").write(get(f"https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{y}FD.zip"))
            except Exception as e: print("zip fail",y,e); continue
        try: root=ET.fromstring(zipfile.ZipFile(zpath).read(f"{y}FD.xml"))
        except Exception as e: print("xml fail",y,e); continue
        for mem in root:
            if mem.findtext("FilingType")!="P": continue
            sd=(mem.findtext("StateDst") or "").strip()
            out.append(dict(year=y, last=mem.findtext("Last") or "", first=mem.findtext("First") or "",
                            state=sd[:2], district=sd[2:], filing_date=mem.findtext("FilingDate"),
                            docid=(mem.findtext("DocID") or "").strip()))
    return out

def fetch_pdf(rec):
    doc=rec["docid"]
    if not doc.isdigit(): return None
    path=os.path.join(CACHE,f"{doc}.pdf")
    if not os.path.exists(path) or os.path.getsize(path)<1000:
        try: open(path,"wb").write(get(f"https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{rec['year']}/{doc}.pdf",30))
        except Exception: return None
    return path

def parse_pdf(path):
    try: txt=subprocess.run(["pdftotext","-layout",path,"-"],capture_output=True,text=True,timeout=30).stdout
    except Exception: return []
    rows=[]; prev=0
    for t in TAG.finditer(txt):
        chunk=txt[prev:t.end()]; prev=t.end()
        if t.group(1)!="ST": continue
        a=ANCHOR.search(chunk)
        if not a: continue
        typ,td,nd=a.groups()
        cands=re.findall(r'\(([A-Za-z0-9.\-]{1,9})\)',chunk)
        ticker=next((c for c in reversed(cands) if TICKER_RE.match(c)),None)
        if not ticker: continue
        am=AMT.search(chunk[a.end():])
        usd=(int(am.group(1).replace(",",""))+int(am.group(2).replace(",","")))/2 if am else None
        rows.append((typ,td,nd,ticker,usd))
    return rows

def process(rec):
    path=fetch_pdf(rec)
    if not path: return []
    out=[]
    for typ,td,nd,tk,usd in parse_pdf(path):
        out.append(dict(party=party_of(rec["last"],rec["state"],rec["district"]),
                        member=f'{rec["first"]} {rec["last"]}'.strip(), chamber="House", state=rec["state"],
                        ticker=tk, type=typ, transaction_date=td, filing_date=rec["filing_date"], amount=usd))
    return out

def main():
    F=filings()
    print(f"PTR 신고: {len(F)}건 ({YEARS[0]}~{YEARS[-1]})  다운로드·파싱…")
    allrows=[]
    with ThreadPoolExecutor(max_workers=24) as ex:
        for i,res in enumerate(ex.map(process,F)):
            allrows.extend(res)
            if (i+1)%300==0: print(f"  {i+1}/{len(F)} | {len(allrows)} tx")
    df=pd.DataFrame(allrows)
    for c in ["transaction_date","filing_date"]:
        df[c]=pd.to_datetime(df[c],format="%m/%d/%Y",errors="coerce")
    df=df.dropna(subset=["transaction_date","filing_date"])
    df=df[(df["transaction_date"]>="2012-06-01")&(df["transaction_date"]<="2026-05-22")]
    df["lag_days"]=(df["filing_date"]-df["transaction_date"]).dt.days
    df=df[(df["lag_days"]>=0)&(df["lag_days"]<=500)]
    df=df.drop_duplicates(subset=["member","ticker","type","transaction_date","filing_date","amount"])
    df.to_csv(os.path.join(DATA,"congress_ptr_transactions.csv"),index=False)
    print(f"\n저장 {len(df)} → data/congress_ptr_transactions.csv  ({df.transaction_date.min().date()}~{df.transaction_date.max().date()})")
    print("정당:",df["party"].value_counts().to_dict()," 매수/매도:",df["type"].value_counts().to_dict())
    print("금액 파싱율: %.0f%%"%(100*df.amount.notna().mean()))

if __name__=="__main__":
    main()
