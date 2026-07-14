#!/usr/bin/env python3
"""정책정보 모자이크 — 공개 발자국으로 '사적 정책정보' 흐름 역추적.
핵심: 사적 tip은 비관측이나, 그 발자국(로비$·계약·의원거래·법안)이 공개 데이터에 흩어져 있다.
이 스크립트는 그 1층(로비)·2층(연방계약)을 기업별로 수집 — 키 불요.
  ① 로비: Senate LDA API (lda.senate.gov/api) — 기업별 분기 로비지출·이슈·법안
  ② 계약: USASpending API — 기업별 연방 수주
한계: 모자이크는 정황(상관)이지 증명 아님. 분기 공시·후행이라 실시간 엣지 아님. 대기업 base-rate 보정 필요."""
import os, re, json, time, urllib.request, urllib.parse, collections
import pandas as pd
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
UA={"User-Agent": os.environ.get("SEC_USER_AGENT", "research your-email@example.com")}
def jget(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30).read())
    except Exception: return {}
def jpost(u,payload):
    try:
        r=urllib.request.Request(u,data=json.dumps(payload).encode(),headers={**UA,"Content-Type":"application/json"})
        return json.loads(urllib.request.urlopen(r,timeout=30).read())
    except Exception: return {}

# 보유종목 → 로비 client명 (ETF 상위 + 정책민감)
CLIENTS={"NVDA":"NVIDIA","INTC":"Intel Corporation","AMD":"Advanced Micro Devices","ANET":"Arista Networks",
 "AVGO":"Broadcom","AAPL":"Apple Inc","MSFT":"Microsoft","GOOG":"Alphabet","AMZN":"Amazon.com","JPM":"JPMorgan Chase",
 "PLTR":"Palantir","UTHR":"United Therapeutics","FIX":"Comfort Systems","AMAT":"Applied Materials","T":"AT&T"}
BILL=re.compile(r'\b([HS]\.?\s?(?:R\.?|J\.?\s?Res\.?|Con\.?\s?Res\.?)?\s?\d{1,5})\b')

def lobbying(client,year):
    tot=0.0; n=0; issues=collections.Counter(); bills=set()
    url=f"https://lda.senate.gov/api/v1/filings/?client_name={urllib.parse.quote(client)}&filing_year={year}&page_size=25"
    while url:
        d=jget(url)
        if "results" not in d: break
        for f in d["results"]:
            amt=f.get("income") or f.get("expenses") or 0
            try: tot+=float(amt)
            except Exception: pass
            n+=1
            for a in f.get("lobbying_activities",[]):
                gi=a.get("general_issue_code_display") or a.get("general_issue_code")
                if gi: issues[gi]+=1
                for m in BILL.findall(a.get("description","") or ""): bills.add(m.replace(" ",""))
        url=d.get("next"); time.sleep(0.2)
    return tot,n,issues.most_common(3),sorted(bills)[:6]

def contracts(name,start,end):
    d=jpost("https://api.usaspending.gov/api/v2/search/spending_by_award/",{
        "filters":{"award_type_codes":["A","B","C","D"],"recipient_search_text":[name],
                   "time_period":[{"start_date":start,"end_date":end}]},
        "fields":["Award Amount","Recipient Name"],"limit":50})
    tot=sum(r.get("Award Amount",0) or 0 for r in d.get("results",[]) if name.split()[0].upper() in str(r.get("Recipient Name","")).upper())
    return tot

rows=[]
for tk,cl in CLIENTS.items():
    l24,_,_,_=lobbying(cl,2024); l25,n25,iss,bills=lobbying(cl,2025)
    rows.append(dict(ticker=tk,client=cl,lobby_2024=l24,lobby_2025=l25,
                     변화배수=round(l25/l24,1) if l24 else None,이슈="·".join(i for i,_ in iss),법안=" ".join(bills)))
    print(f"{tk:5} 로비 24:${l24/1e6:.2f}M → 25:${l25/1e6:.2f}M  ({'x%.1f'%(l25/l24) if l24 else 'NEW' if l25 else '없음'})  {[i for i,_ in iss]}")
df=pd.DataFrame(rows).sort_values("lobby_2025",ascending=False)
df.to_csv(os.path.join(DATA,"policy_mosaic_lobbying.csv"),index=False)
print("\n저장: data/policy_mosaic_lobbying.csv")
print("\n해석: 로비$ 급증 + 관할위원 거래(PTR) + 계약/규칙 결과가 '시간순 군집'하면 정책정보 흐름 의심(모자이크).")
