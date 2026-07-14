#!/usr/bin/env python3
"""⑥ 전사 확대 — nexus 등장 전(全) 기업의 PAC→의원 자금엣지. .env 키, 율제한 無.
universe=conflict_nexus 종목. 이름=yfinance(캐시). 출력: data/pac_member_funding.csv (확대)."""
import os,sys,json,time,urllib.request,urllib.parse,pandas as pd,yfinance as yf
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from _config import FEC_API_KEY as KEY
DATA=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"data"); B="https://api.open.fec.gov/v1"
OV={"GOOGL":"Google","GOOG":"Google","QCOM":"Qualcomm","VZ":"Verizon","DIS":"Walt Disney","TSLA":"Tesla","UNH":"UnitedHealth","CMCSA":"Comcast","CHTR":"Charter","T":"AT&T","NFLX":"Netflix","X":"United States Steel","BRK.B":"Berkshire","META":"Meta","AVGO":"Broadcom"}
def get(u):
    try: return json.loads(urllib.request.urlopen(u,timeout=25).read())
    except Exception: return {}
univ=sorted(pd.read_csv(os.path.join(DATA,"conflict_nexus.csv")).종목.unique())
CF=os.path.join(DATA,"_client_names.json"); cli=json.load(open(CF)) if os.path.exists(CF) else {}
todo=[t for t in univ if t not in cli]
def nm(t):
    try: return t,(yf.Ticker(t.replace(".","-")).info.get("shortName") or t)
    except: return t,t
if todo:
    with ThreadPoolExecutor(max_workers=12) as ex:
        for t,n in ex.map(nm,todo):
            c=n.split(",")[0]
            for s in [" Inc"," Corporation"," Corp"," Co"," Ltd"," plc"," Company"," Holdings"," Group"," Platforms","."]: c=c.replace(s," ")
            cli[t]=c.strip()
    json.dump(cli,open(CF,"w"))
def find_pac(tk):
    for q in [OV.get(tk),cli.get(tk),(cli.get(tk) or "").split()[0] if cli.get(tk) else None]:
        if not q or len(q)<3: continue
        d=get(f"{B}/committees/?q={urllib.parse.quote(q)}&committee_type=Q&api_key={KEY}&per_page=1&sort=-receipts")
        if d.get("results"): return d["results"][0]["committee_id"]
    return None
def recips(pid):
    d=get(f"{B}/schedules/schedule_b/by_recipient/?committee_id={pid}&cycle=2024&api_key={KEY}&per_page=100&sort=-total")
    return [(r.get("recipient_name","") or "",r.get("total",0)) for r in d.get("results",[])]
leg=pd.read_csv("https://unitedstates.github.io/congress-legislators/legislators-current.csv")
leg=leg[leg.type.isin(["sen","rep"])][["last_name","first_name","state","party"]].dropna()
LEG=[(str(r.last_name),str(r.first_name),r.state,r.party) for _,r in leg.iterrows()]
edges=[]; npac=0
for i,tk in enumerate(univ):
    pid=find_pac(tk)
    if not pid: continue
    npac+=1
    for rn,tot in recips(pid):
        ru=rn.upper()
        for ln,fn,st,pty in LEG:
            if ln.upper() in ru and (fn.upper() in ru or len(ln)>=7):
                edges.append(dict(ticker=tk,member_last=ln,member_first=fn,state=st,party=pty,amount=round(tot)))
    if (i+1)%40==0: print(f"  {i+1}/{len(univ)} | PAC {npac} | 엣지 {len(edges)}")
    time.sleep(0.2)
df=pd.DataFrame(edges).drop_duplicates(subset=["ticker","member_last","member_first"])
df.to_csv(os.path.join(DATA,"pac_member_funding.csv"),index=False)
print(f"\n확대 완료: {len(univ)}기업 중 PAC {npac}개 식별 | 기업→의원 자금엣지 {len(df)}건")
