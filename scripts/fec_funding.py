#!/usr/bin/env python3
"""⑥ 정밀 — 기업 PAC → 개별 의원 자금 엣지. .env의 FEC_API_KEY 사용.
PAC명 매칭 개선(override) + by_recipient top100 → 현직 의원(성+이름) 매칭. 출력: data/pac_member_funding.csv"""
import os,sys,json,time,urllib.request,urllib.parse,pandas as pd
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from _config import FEC_API_KEY as KEY
DATA=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"data"); B="https://api.open.fec.gov/v1"
OV={"GOOGL":"Google","GOOG":"Google","QCOM":"Qualcomm","VZ":"Verizon","DIS":"Walt Disney","TSLA":"Tesla",
 "UNH":"UnitedHealth","CMCSA":"Comcast","CHTR":"Charter","T":"AT&T","NFLX":"Netflix","MNST":"Monster",
 "X":"United States Steel","STX":"Seagate","DDOG":"Datadog","MDB":"MongoDB","FWONK":"Liberty Media","LBRDK":"Liberty"}
def get(u):
    try: return json.loads(urllib.request.urlopen(u,timeout=25).read())
    except Exception: return {}
def find_pac(tk,client):
    for q in [OV.get(tk),client,client.split()[0] if client else None]:
        if not q: continue
        d=get(f"{B}/committees/?q={urllib.parse.quote(q)}&committee_type=Q&api_key={KEY}&per_page=1&sort=-receipts")
        r=d.get("results",[])
        if r: return r[0]["committee_id"],r[0]["name"]
    return None,None
def recips(pid,n=100):
    d=get(f"{B}/schedules/schedule_b/by_recipient/?committee_id={pid}&cycle=2024&api_key={KEY}&per_page={n}&sort=-total")
    return [(r.get("recipient_name","") or "",r.get("total",0)) for r in d.get("results",[])]
leg=pd.read_csv("https://unitedstates.github.io/congress-legislators/legislators-current.csv")
leg=leg[leg.type.isin(["sen","rep"])][["last_name","first_name","state","party"]].dropna()
clients=pd.read_csv(os.path.join(DATA,"policy_footprint_panel.csv"))[["ticker","client"]].drop_duplicates()
edges=[]; npac=0
for _,c in clients.iterrows():
    pid,pnm=find_pac(c.ticker,c.client)
    if not pid: print(f"  {c.ticker}: PAC無"); continue
    npac+=1; rs=recips(pid)
    for rn,tot in rs:
        ru=rn.upper()
        for _,m in leg.iterrows():
            ln=m.last_name.upper(); fn=m.first_name.upper()
            if ln in ru and (fn in ru or len(ln)>=7):   # 성+이름(또는 긴 성)로 정밀매칭
                edges.append(dict(ticker=c.ticker,member_last=m.last_name,member_first=m.first_name,
                                  state=m.state,party=m.party,recipient=rn,amount=round(tot)))
    print(f"  {c.ticker}: {pnm[:30] if pnm else ''} → 의원엣지 {sum(1 for e in edges if e['ticker']==c.ticker)}")
    time.sleep(0.25)
df=pd.DataFrame(edges).drop_duplicates(subset=["ticker","member_last","member_first"])
df.to_csv(os.path.join(DATA,"pac_member_funding.csv"),index=False)
print(f"\nPAC 식별 {npac}/{len(clients)} | 기업→의원 자금엣지 {len(df)}건 → data/pac_member_funding.csv")
