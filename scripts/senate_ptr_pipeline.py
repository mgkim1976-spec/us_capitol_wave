#!/usr/bin/env python3
"""상원 eFD PTR 파이프라인 — curl_cffi(Chrome TLS 모사)로 Akamai WAF 우회.
발견: eFD 차단은 IP가 아니라 TLS 핑거프린트 → curl_cffi impersonate='chrome'으로 200 응답.
플로우: 동의 POST → report/data JSON(신고목록) → 각 PTR HTML 테이블 파싱.
출력: data/senate_ptr_transactions.csv  (하원과 동일 스키마 + chamber='Senate')."""
import os, re, csv, time
import pandas as pd
from curl_cffi import requests as creq
from concurrent.futures import ThreadPoolExecutor
import threading

HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
B="https://efdsearch.senate.gov"
START="01/01/2013 00:00:00"

def new_session():
    s=creq.Session(impersonate="chrome")
    r=s.get(B+"/search/home/",timeout=30)
    tok=re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"',r.text).group(1)
    s.post(B+"/search/home/",data={"csrfmiddlewaretoken":tok,"prohibition_agreement":"1"},
           headers={"Referer":B+"/search/home/"},timeout=30)
    s.get(B+"/search/",timeout=30)
    return s

# ---- party map (senate) ----
def load_party():
    nd={}
    for fn in ["legislators-current.csv","legislators-historical.csv"]:
        p=os.path.join("/tmp",fn)
        for r in csv.DictReader(open(p)):
            if r["type"]!="sen": continue
            nd.setdefault(r["last_name"].strip().lower(), r["party"][:1].upper())
    return nd
PARTY=load_party()
def party_of(last): return PARTY.get(last.strip().lower(),"?")

# ---- 1) 신고목록 ----
def list_filings():
    s=new_session(); csrf=s.cookies.get("csrftoken"); out=[]; start=0
    while True:
        payload={"draw":"1","start":str(start),"length":"100","report_types":"[11]","filer_types":"[]",
         "submitted_start_date":START,"submitted_end_date":"","search[value]":"",
         "order[0][column]":"4","order[0][dir]":"desc"}
        d=s.post(B+"/search/report/data/",data=payload,
                 headers={"Referer":B+"/search/","X-CSRFToken":csrf,"X-Requested-With":"XMLHttpRequest"},timeout=30).json()
        rows=d.get("data",[])
        for row in rows:
            h=re.search(r'href="([^"]+)"',row[3])
            if not h or "/ptr/" not in h.group(1): continue   # electronic only
            out.append(dict(first=re.sub(r'<[^>]+>','',row[0]).strip(),
                            last=re.sub(r'<[^>]+>','',row[1]).strip(),
                            href=h.group(1), filing_date=row[4].strip()))
        total=d.get("recordsTotal",0); start+=100
        if start>=total or not rows: break
        time.sleep(0.2)
    return out

# ---- 2) PTR 상세 파싱 ----
_loc=threading.local()
def sess():
    if not hasattr(_loc,"s"): _loc.s=new_session()
    return _loc.s
def parse_ptr(rec):
    try:
        html=sess().get(B+rec["href"],timeout=30).text
    except Exception:
        return []
    out=[]
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>',html,re.S):
        c=[re.sub(r'<[^>]+>','',x).strip() for x in re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)]
        if len(c)<8: continue
        tdate,owner,ticker,asset,atype,ttype,amount=c[1],c[2],c[3],c[4],c[5],c[6],c[7]
        if "stock" not in atype.lower(): continue
        if not re.match(r'^[A-Z]{1,5}(\.[A-Z]{1,2})?$',ticker): continue
        typ="P" if ttype.lower().startswith("purchase") else ("S" if "sale" in ttype.lower() else "E")
        out.append(dict(party=party_of(rec["last"]), member=f'{rec["first"]} {rec["last"]}',
                        chamber="Senate", ticker=ticker, type=typ, transaction_date=tdate,
                        filing_date=rec["filing_date"], owner=owner, amount=amount))
    return out

def main():
    F=list_filings()
    print(f"상원 전자 PTR 신고: {len(F)}건  파싱…")
    rows=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i,res in enumerate(ex.map(parse_ptr,F)):
            rows.extend(res)
            if (i+1)%50==0: print(f"  {i+1}/{len(F)} | {len(rows)} tx")
    df=pd.DataFrame(rows)
    for c in ["transaction_date","filing_date"]:
        df[c]=pd.to_datetime(df[c],format="%m/%d/%Y",errors="coerce")
    df=df.dropna(subset=["transaction_date","filing_date"])
    df=df[(df.transaction_date>="2012-06-01")&(df.transaction_date<="2026-05-22")]
    df["lag_days"]=(df.filing_date-df.transaction_date).dt.days
    df=df[(df.lag_days>=0)&(df.lag_days<=400)]
    df=df.drop_duplicates(subset=["member","ticker","type","transaction_date","filing_date"])
    df.to_csv(os.path.join(DATA,"senate_ptr_transactions.csv"),index=False)
    print(f"\n저장 {len(df)} → data/senate_ptr_transactions.csv")
    print("정당:",df.party.value_counts().to_dict()," 매수/매도:",df.type.value_counts().to_dict())
    print("매핑실패:",f"{(df.party=='?').mean()*100:.1f}%")

if __name__=="__main__": main()
