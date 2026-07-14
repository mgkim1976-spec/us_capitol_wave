#!/usr/bin/env python3
"""이해상충 nexus (정밀판) — 6층 결합. 현직 의원만(legislators-current)·성+이름 매칭으로 오매칭 제거.
충돌 삼각형: [③거래 + ④관할위원회 + ⑥기업PAC→그 의원 후원] + ①로비 맥락. 출력: data/conflict_nexus.csv"""
import os,re,pandas as pd,numpy as np
DATA=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"data")
CRYPTO={"IBIT","BITB","BITO","FBTC","GBTC","ARKB","BTCO","ETHA","BITW","MSTR","COIN"}
KOR={"Technology":"기술/반도체","Financial Services":"금융","Healthcare":"헬스케어","Energy":"에너지","Industrials":"산업재","Consumer Cyclical":"경기소비재","Consumer Defensive":"필수소비재","Communication Services":"커뮤니케이션","Basic Materials":"소재"}
JURIS={"기술/반도체":["Commerce","Science","Energy and Commerce","Judiciary"],"금융":["Financial Services","Banking"],
 "에너지":["Energy","Natural Resources","Environment"],"헬스케어":["Health","Finance","Ways and Means","Energy and Commerce","Aging"],
 "산업재":["Armed Services","Transportation","Homeland","Infrastructure"],"커뮤니케이션":["Commerce","Energy and Commerce","Judiciary"],
 "소재":["Natural Resources","Energy","Environment"]}
SUF={"jr","sr","ii","iii","iv","v"}
def parse(member):
    toks=[t.strip(".,") for t in str(member).replace(","," ").split() if t.strip(".,")]
    toks2=[t for t in toks if t.lower() not in SUF]
    if not toks2: return None,None
    return toks2[-1].lower(), toks2[0][:1].lower()   # (성, 이름이니셜)
sc=pd.read_csv(os.path.join(DATA,"ticker_sectors.csv")).set_index("ticker")["sector"].to_dict()
def theme(t): return "암호화폐" if t in CRYPTO else KOR.get(sc.get(t))
# 현직 의원 (성,이니셜)
leg=pd.read_csv("https://unitedstates.github.io/congress-legislators/legislators-current.csv")
CUR={(str(r.last_name).lower(),str(r.first_name)[:1].lower()) for _,r in leg.iterrows()}
# ④ 위원회 (현재 명부) → (성,이니셜)→위원회
cm=pd.read_csv("https://unitedstates.github.io/congress-legislators/committee-membership-current.csv")
m2c={}
for _,r in cm.iterrows():
    k=parse(r["name"]);
    if k[0]: m2c.setdefault(k,set()).add(str(r["committee_name"]))
# ⑥ 기업→의원 자금엣지
fund=set()
try:
    pf=pd.read_csv(os.path.join(DATA,"pac_member_funding.csv"))
    for _,r in pf.iterrows(): fund.add((r.ticker,str(r.member_last).lower(),str(r.member_first)[:1].lower()))
except Exception: pass
# ① 로비
lob=pd.read_csv(os.path.join(DATA,"policy_footprint_panel.csv")); lob25=lob[lob.year==2025].set_index("ticker")["lobby"].to_dict()
# ③ 거래
d=pd.read_csv(os.path.join(DATA,"combined_2019_2026.csv")); d["amount"]=pd.to_numeric(d["amount"],errors="coerce")
d["signed"]=np.where(d.type=="P",d.amount,np.where(d.type=="S",-d.amount,0))
pk=d.member.map(parse); d["last"]=[k[0] for k in pk]; d["fi"]=[k[1] for k in pk]; d["theme"]=d.ticker.map(theme)
rows=[]
g=d[d.theme.notna()].groupby(["member","last","fi","ticker","theme"]).agg(n=("type","size"),net=("signed","sum"),party=("party","first")).reset_index()
for _,r in g.iterrows():
    key=(r["last"],r["fi"])
    if key not in CUR: continue            # ★ 현직만 (Perdue 등 퇴임자 제거)
    cmts=m2c.get(key,set())
    if not cmts: continue
    overseen=[c for c in cmts if any(j in c for j in JURIS.get(r["theme"],[]))]
    if not overseen: continue              # ★ 충돌: 관할 섹터 거래
    funded=(r["ticker"],r["last"],r["fi"]) in fund    # ⑥ 그 기업이 이 의원 후원?
    rows.append(dict(의원=r["member"],정당=r["party"],섹터=r["theme"],종목=r["ticker"],
                     관할위원회=overseen[0][:42],거래수=r["n"],순매수K=round(r["net"]/1e3),
                     기업로비M=round(lob25.get(r["ticker"],0),1),PAC후원=("예" if funded else "")))
nx=pd.DataFrame(rows)
nx["score"]=nx.거래수+(nx.기업로비M>1).astype(int)*2+(nx.PAC후원=="예").astype(int)*6
nx=nx.sort_values(["PAC후원","score"],ascending=[False,False])
nx.to_csv(os.path.join(DATA,"conflict_nexus.csv"),index=False)
print(f"이해상충 nexus(현직): {len(nx)}건 · 의원 {nx.의원.nunique()}명")
print(f"★ 3중충돌(거래+관할+자금): {(nx.PAC후원=='예').sum()}건")
print("\n=== 상위 nexus ===")
print(nx.head(16)[["의원","정당","섹터","종목","관할위원회","거래수","기업로비M","PAC후원"]].to_string(index=False))
