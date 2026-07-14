#!/usr/bin/env python3
"""① 로비 + ② 연방계약 통합 패널 (기업×연도, 2020~2025) — 부분층 ①② 운영 승격.
의회 거래 상위 종목 universe × 연도별 로비$(LDA)·연방계약$(USASpending). 키 불요. 월간 자동화 편입용.
출력: data/policy_footprint_panel.csv"""
import os,re,json,time,urllib.request,urllib.parse,pandas as pd,numpy as np,yfinance as yf
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
UA={"User-Agent": os.environ.get("SEC_USER_AGENT", "research your-email@example.com")}
def jget(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30).read())
    except Exception: return {}
def jpost(u,p):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,data=json.dumps(p).encode(),headers={**UA,"Content-Type":"application/json"}),timeout=30).read())
    except Exception: return {}
d=pd.read_csv(os.path.join(DATA,"combined_2019_2026.csv")); d["amount"]=pd.to_numeric(d["amount"],errors="coerce")
UNIV=[t for t in d.groupby("ticker").amount.sum().sort_values(ascending=False).index if re.match(r'^[A-Z]{1,5}$',t)][:35]
# client명 (yfinance, 캐시)
CF=os.path.join(DATA,"_client_names.json")
cli=json.load(open(CF)) if os.path.exists(CF) else {}
for tk in UNIV:
    if tk in cli: continue
    try: nm=yf.Ticker(tk.replace(".","-")).info.get("shortName") or tk
    except: nm=tk
    c=nm.split(",")[0]
    for s in [" Inc"," Corporation"," Corp"," Co"," Ltd"," plc"," Company"," Holdings"," Group"," Platforms","."]: c=c.replace(s," ")
    cli[tk]=c.strip()
json.dump(cli,open(CF,"w"))
def lobby(c,y):
    t=0;url=f"https://lda.senate.gov/api/v1/filings/?client_name={urllib.parse.quote(c)}&filing_year={y}&page_size=25";h=0
    while url and h<5:
        j=jget(url)
        if "results" not in j: break
        for f in j["results"]:
            try:t+=float(f.get("income") or f.get("expenses") or 0)
            except:pass
        url=j.get("next");h+=1;time.sleep(0.1)
    return t
def contracts(name,y):
    j=jpost("https://api.usaspending.gov/api/v2/search/spending_by_award/",{"filters":{"award_type_codes":["A","B","C","D"],"recipient_search_text":[name],"time_period":[{"start_date":f"{y}-01-01","end_date":f"{y}-12-31"}]},"fields":["Award Amount","Recipient Name"],"limit":100})
    k=name.split()[0].upper()
    return sum((r.get("Award Amount") or 0) for r in j.get("results",[]) if k in str(r.get("Recipient Name","")).upper())
rows=[]
for tk in UNIV:
    c=cli[tk]
    for y in range(2020,2026):
        rows.append(dict(ticker=tk,client=c,year=y,lobby=round(lobby(c,y)/1e6,2),contracts=round(contracts(c,y)/1e6,1)))
    print(f"{tk} done")
df=pd.DataFrame(rows); df.to_csv(os.path.join(DATA,"policy_footprint_panel.csv"),index=False)
print(f"\n저장 {len(df)} 기업-연도 → data/policy_footprint_panel.csv")
print("로비 상위(2025):"); print(df[df.year==2025].nlargest(6,"lobby")[["ticker","lobby","contracts"]].to_string(index=False))
