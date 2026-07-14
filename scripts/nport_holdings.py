#!/usr/bin/env python3
"""SEC N-PORT 전체보유 파싱 → NANC/GOP 전체 신규·청산·확대·축소 (분기 시계열, 2023~).
정식명칭 FTS로 전 분기 N-PORT 발견(과거분은 generic 파일명). 보유는 primary_doc.xml.
출력: data/nport_holdings/{fund}_{period}.csv, {fund}_changes.json(최신쌍), {fund}_timeseries.csv."""
import os, re, json, urllib.request, urllib.parse
import pandas as pd
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
ND=os.path.join(DATA,"nport_holdings"); os.makedirs(ND,exist_ok=True)
UA={"User-Agent": os.environ.get("SEC_USER_AGENT", "research your-email@example.com")}
NAMES={"NANC":"Subversive Democratic Trading","GOP":"Subversive Republican Trading"}
def get(u):
    try: return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=40).read().decode("utf-8","ignore")
    except Exception: return ""
def fetch_xml(acc):
    base=f"https://www.sec.gov/Archives/edgar/data/1742912/{acc.replace('-','')}/"
    x=get(base+"primary_doc.xml")
    if "<invstOrSec>" in x: return x
    idx=get(base)
    for xf in re.findall(r'href="([^"]+\.xml)"',idx):
        url=xf if xf.startswith("http") else "https://www.sec.gov"+xf
        x=get(url)
        if "<invstOrSec>" in x: return x
    return ""

def discover():
    found={}
    for fund,nm in NAMES.items():
        q=urllib.parse.quote(f'"{nm}"')
        d=json.loads(get(f"https://efts.sec.gov/LATEST/search-index?q={q}&forms=NPORT-P"))
        for h in d["hits"]["hits"]:
            found.setdefault((fund,h["_source"]["period_ending"]),h["_id"].split(":")[0])
    return found

def parse_nport(acc):
    xml=fetch_xml(acc)
    rows=[]
    for b in re.findall(r'<invstOrSec>(.*?)</invstOrSec>',xml,re.S):
        tk=re.search(r'<ticker value="([^"]+)"',b); nm=re.search(r'<name>([^<]+)</name>',b)
        pv=re.search(r'<pctVal>([\d.]+)</pctVal>',b); vu=re.search(r'<valUSD>(-?[\d.]+)</valUSD>',b)
        tkr=tk.group(1).strip() if tk else ""
        if not re.match(r'^[A-Z]{1,6}$',tkr): continue
        rows.append(dict(ticker=tkr,name=nm.group(1).strip() if nm else "",
                         pct=float(pv.group(1)) if pv else 0,valUSD=float(vu.group(1)) if vu else 0))
    if not rows: return pd.DataFrame(columns=["ticker","pct","valUSD","name"])
    return pd.DataFrame(rows).groupby("ticker").agg(pct=("pct","sum"),valUSD=("valUSD","sum"),name=("name","first")).reset_index().sort_values("pct",ascending=False)

found=discover()
print("발견 N-PORT:",len(found),"건")
data={}
for (fund,pe),acc in sorted(found.items()):
    fp=os.path.join(ND,f"{fund}_{pe}.csv")
    if os.path.exists(fp): df=pd.read_csv(fp)
    else:
        df=parse_nport(acc)
        if len(df): df.to_csv(fp,index=False)
    if len(df): data[(fund,pe)]=df

def diff(a,b):  # a=이전, b=최신 (set_index ticker)
    out={"신규":[],"청산":[],"확대":[],"축소":[]}
    for tk in set(a.index)|set(b.index):
        pa=a.pct.get(tk,0); pb=b.pct.get(tk,0); d=round(pb-pa,2)
        if tk not in a.index: out["신규"].append((tk,round(pb,2)))
        elif tk not in b.index: out["청산"].append((tk,round(pa,2)))
        elif d>=0.3: out["확대"].append((tk,d))
        elif d<=-0.3: out["축소"].append((tk,d))
    out["신규"]=sorted(out["신규"],key=lambda x:-x[1]); out["청산"]=sorted(out["청산"],key=lambda x:-x[1])
    out["확대"]=sorted(out["확대"],key=lambda x:-x[1]); out["축소"]=sorted(out["축소"],key=lambda x:x[1])
    return out

for fund in ["NANC","GOP"]:
    pes=sorted([p for f,p in data if f==fund])
    if len(pes)<2: print(f"{fund}: 시점 부족"); continue
    # 시계열 (종목수·상위10비중)
    ts=[]
    for pe in pes:
        df=data[(fund,pe)]; ts.append({"period":pe,"종목수":len(df),"상위10비중":round(df.pct.head(10).sum(),1),"상위1":df.iloc[0].ticker})
    pd.DataFrame(ts).to_csv(os.path.join(ND,f"{fund}_timeseries.csv"),index=False)
    # 최신 쌍 변화
    a=data[(fund,pes[-2])].set_index("ticker"); b=data[(fund,pes[-1])].set_index("ticker")
    dd=diff(a,b); dd["기간"]=f"{pes[-2]} → {pes[-1]}"
    json.dump(dd,open(os.path.join(ND,f"{fund}_changes.json"),"w"),ensure_ascii=False)
    print(f"\n===== {fund} ({pes[0]}~{pes[-1]}, {len(pes)}분기) — 최신변화 {dd['기간']} =====")
    print(f"  종목수 추이: "+" → ".join(f"{t['종목수']}" for t in ts))
    print(f"  🆕 신규({len(dd['신규'])}): "+", ".join(f"{t}(+{p}%)" for t,p in dd['신규'][:10]))
    print(f"  ❌ 청산({len(dd['청산'])}): "+", ".join(f"{t}" for t,p in dd['청산'][:10]))
    print(f"  ▲ 확대: "+", ".join(f"{t}({d:+}%p)" for t,d in dd['확대'][:6]))
    print(f"  ▼ 축소: "+", ".join(f"{t}({d:+}%p)" for t,d in dd['축소'][:6]))
print("\n저장: data/nport_holdings/ (분기 CSV + changes.json + timeseries.csv)")
