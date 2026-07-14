#!/usr/bin/env python3
"""모자이크 종합 패널 — 5개 공개층 × 2020~2025(바이든+트럼프2기) → 익년 초과수익 검정.
층: ①로비(LDA) ②연방계약(USASpending) ③의원순매수(PTR) ④위원회 관할거래(committee) ⑤규제강도(Federal Register)
한계: ④위원회는 현재 명부 스냅샷(시변 아님), ⑤규제는 섹터-기관 근사, ⑥FEC 미포함. 모두 정황(모자이크)이지 증명 아님."""
import os,re,json,time,urllib.request,urllib.parse,collections,numpy as np,pandas as pd,yfinance as yf
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
UA={"User-Agent": os.environ.get("SEC_USER_AGENT", "research your-email@example.com")}
def jget(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30).read())
    except Exception: return {}
def jpost(u,p):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,data=json.dumps(p).encode(),headers={**UA,"Content-Type":"application/json"}),timeout=30).read())
    except Exception: return {}

d=pd.read_csv(os.path.join(DATA,"combined_2019_2026.csv"),parse_dates=["transaction_date"])
d["amount"]=pd.to_numeric(d["amount"],errors="coerce"); d=d.dropna(subset=["amount"])
d["signed"]=np.where(d.type=="P",d.amount,np.where(d.type=="S",-d.amount,0)); d["yr"]=d.transaction_date.dt.year
d["last"]=d.member.str.replace(",","").str.split().str[-1].str.lower()
sec=pd.read_csv(os.path.join(DATA,"ticker_sectors.csv")).set_index("ticker")["sector"].to_dict() if os.path.exists(os.path.join(DATA,"ticker_sectors.csv")) else {}
UNIV=d.groupby("ticker").amount.sum().sort_values(ascending=False)
UNIV=[t for t in UNIV.index if re.match(r'^[A-Z]{1,5}$',t)][:25]

# ④ 위원회: 현재 명부 → 의원 last → 위원회 집합
cm=pd.read_csv("https://unitedstates.github.io/congress-legislators/committee-membership-current.csv")
mem2cmt=collections.defaultdict(set)
for _,r in cm.iterrows():
    mem2cmt[str(r["name"]).split()[-1].lower()].add(str(r["committee_name"]))
JURIS={"Technology":["Commerce","Science","Energy and Commerce"],"Financial Services":["Financial Services","Banking"],
 "Energy":["Energy","Natural Resources","Environment"],"Healthcare":["Health","Finance","Ways and Means","Energy and Commerce"],
 "Industrials":["Armed Services","Transportation","Homeland"],"Communication Services":["Commerce","Energy and Commerce"],
 "Consumer Cyclical":["Ways and Means","Financial"],"Basic Materials":["Natural Resources","Energy"]}
FR_AG={"Technology":["commerce-department","federal-communications-commission"],"Financial Services":["treasury-department","securities-and-exchange-commission"],
 "Energy":["energy-department","environmental-protection-agency"],"Healthcare":["health-and-human-services-department","food-and-drug-administration"],
 "Industrials":["defense-department","transportation-department"],"Communication Services":["federal-communications-commission"]}

def lobby(client,y):
    t=0;url=f"https://lda.senate.gov/api/v1/filings/?client_name={urllib.parse.quote(client)}&filing_year={y}&page_size=25";h=0
    while url and h<5:
        j=jget(url)
        if "results" not in j:break
        for f in j["results"]:
            try:t+=float(f.get("income") or f.get("expenses") or 0)
            except:pass
        url=j.get("next");h+=1;time.sleep(0.1)
    return t
def contracts(name,y):
    j=jpost("https://api.usaspending.gov/api/v2/search/spending_by_award/",{"filters":{"award_type_codes":["A","B","C","D"],"recipient_search_text":[name],"time_period":[{"start_date":f"{y}-01-01","end_date":f"{y}-12-31"}]},"fields":["Award Amount","Recipient Name"],"limit":100})
    key=name.split()[0].upper()
    return sum((r.get("Award Amount") or 0) for r in j.get("results",[]) if key in str(r.get("Recipient Name","")).upper())
FRcache={}
def reg(sector,y):
    ags=FR_AG.get(sector,[]); tot=0
    for a in ags:
        k=(a,y)
        if k not in FRcache:
            j=jget(f"https://www.federalregister.gov/api/v1/documents.json?conditions%5Btype%5D=RULE&conditions%5Bagencies%5D%5B%5D={a}&conditions%5Bpublication_date%5D%5Bgte%5D={y}-01-01&conditions%5Bpublication_date%5D%5Blte%5D={y}-12-31&per_page=1")
            FRcache[k]=j.get("count",0); time.sleep(0.1)
        tot+=FRcache[k]
    return tot

# 가격 → 연말 종가 → 익년 초과수익
ytk=[t.replace(".","-") for t in UNIV]
px=yf.download(ytk+["SPY"],start="2019-06-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
ye=px.resample("YE").last(); ye.index=ye.index.year
def fwd(tk,y):  # y년말→y+1년말 (2025는 y말→2026-05-22)
    c=tk.replace(".","-")
    if c not in px: return None
    if y+1 in ye.index and not pd.isna(ye.loc[y,c]) and not pd.isna(ye.loc[y+1,c]):
        r=ye.loc[y+1,c]/ye.loc[y,c]-1; rs=ye.loc[y+1,"SPY"]/ye.loc[y,"SPY"]-1; return (r-rs)*100
    if y==2025 and not pd.isna(ye.loc[2025,c]):
        last=px[c].dropna().iloc[-1]; r=last/ye.loc[2025,c]-1; rs=px["SPY"].dropna().iloc[-1]/ye.loc[2025,"SPY"]-1; return (r-rs)*100
    return None

# client명 (yfinance, 캐시)
cli={}
for tk in UNIV:
    try: nm=yf.Ticker(tk.replace(".","-")).info.get("shortName") or tk
    except: nm=tk
    c=nm.split(",")[0]
    for s in [" Inc"," Corporation"," Corp"," Co"," Ltd"," plc"," Company"," Holdings"," Group"," Platforms",", Inc."]: c=c.replace(s," ")
    cli[tk]=c.strip()

rows=[]
for tk in UNIV:
    s=sec.get(tk); skor=s if s in JURIS else None
    for y in range(2020,2026):
        fx=fwd(tk,y)
        if fx is None: continue
        ty=d[(d.ticker==tk)&(d.yr==y)]
        nb=ty.signed.sum()/1e6; nm=ty.member.nunique()
        # 관할위원 거래수
        jset=JURIS.get(s,[]) if s else []
        cov=sum(1 for _,r in ty.iterrows() if any(any(j in c for c in mem2cmt.get(r["last"],set())) for j in jset)) if jset else 0
        rows.append(dict(ticker=tk,year=y,sector=s,lobby=lobby(cli[tk],y)/1e6,contracts=contracts(cli[tk],y)/1e6,
                         netbuy=round(nb,2),members=nm,cmt_trades=cov,reg=reg(s,y) if s in FR_AG else 0,fwd_exc=round(fx,1)))
    print(f"{tk} done")
pd.DataFrame(rows).to_csv(os.path.join(DATA,"mosaic_panel.csv"),index=False)
print(f"\n패널 저장 {len(rows)} obs → data/mosaic_panel.csv")
