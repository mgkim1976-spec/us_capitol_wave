#!/usr/bin/env python3
"""⑥ 자금층 — 기업→PAC→수령 의원/위원회 (FEC). FEC_API_KEY 환경변수 사용(없으면 DEMO_KEY, 율제한).
출력: data/company_pac.csv (기업→PAC), data/pac_recipients.csv (PAC→수령자 집계, 2024 사이클)."""
import os,json,time,urllib.request,urllib.parse,pandas as pd
DATA=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"data")
KEY=os.environ.get("FEC_API_KEY","DEMO_KEY"); B="https://api.open.fec.gov/v1"
def get(u):
    try: return json.loads(urllib.request.urlopen(u,timeout=25).read())
    except Exception: return {}
def pac(q):
    d=get(f"{B}/committees/?q={urllib.parse.quote(q)}&committee_type=Q&api_key={KEY}&per_page=1&sort=-receipts")
    r=d.get("results",[]); return (r[0]["committee_id"],r[0]["name"]) if r else (None,None)
def recipients(pid,cycle=2024,n=8):
    d=get(f"{B}/schedules/schedule_b/by_recipient/?committee_id={pid}&cycle={cycle}&api_key={KEY}&per_page={n}&sort=-total")
    return [(r.get("recipient_name",""),r.get("total",0)) for r in d.get("results",[])]
clients=pd.read_csv(os.path.join(DATA,"policy_footprint_panel.csv"))[["ticker","client"]].drop_duplicates()
rows=[]; rec=[]
for _,r in clients.iterrows():
    cid,nm=pac(r.client); rows.append(dict(ticker=r.ticker,client=r.client,pac_id=cid,pac_name=nm))
    if cid and cid not in (None,"rate_limit?"):
        for rn,tot in recipients(cid): rec.append(dict(ticker=r.ticker,pac=cid,recipient=rn,total_2024=round(tot)))
        print(f"  {r.ticker}: {nm[:34] if nm else ''} → 수령자 {sum(1 for x in rec if x['ticker']==r.ticker)}")
    else: print(f"  {r.ticker}: PAC 없음")
    time.sleep(0.3)
pd.DataFrame(rows).to_csv(os.path.join(DATA,"company_pac.csv"),index=False)
pd.DataFrame(rec).to_csv(os.path.join(DATA,"pac_recipients.csv"),index=False)
pacn=pd.DataFrame(rows).pac_id.apply(lambda x:bool(x) and x not in(None,"rate_limit?")).sum()
print(f"\n저장: company_pac.csv (PAC식별 {pacn}/{len(rows)}), pac_recipients.csv ({len(rec)} 기업-수령자)")
