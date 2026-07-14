#!/usr/bin/env python3
"""정책 → 섹터 로테이션 검정 (단위=섹터, 섹터중립 안 함).
사용자 통찰: 정책은 섹터를 통해 드러난다 → 섹터를 중립화하면 신호를 지운다.
그러니 섹터별 정책신호(의회 순매수·규제강도)가 *다음 해 섹터 초과수익*을 예측하는지(선행) 검정.
선행(정책 t → 섹터수익 t+1) vs 동행(t→t) 비교로 '이미 반영 vs 예측력' 판별."""
import os,re,json,time,urllib.request,collections,numpy as np,pandas as pd,yfinance as yf
from scipy.stats import pearsonr
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
UA={"User-Agent": os.environ.get("SEC_USER_AGENT", "research your-email@example.com")}
def jget(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30).read())
    except Exception: return {}
# 섹터 매핑 (재사용)
CRYPTO={"IBIT","BITB","BITO","FBTC","GBTC","ARKB","BTCO","ETHA","BITW","MSTR","COIN","BITX"}
KOR={"Technology":"기술/반도체","Financial Services":"금융","Healthcare":"헬스케어","Energy":"에너지","Industrials":"산업재",
 "Consumer Cyclical":"경기소비재","Consumer Defensive":"필수소비재","Communication Services":"커뮤니케이션","Basic Materials":"소재"}
sc=pd.read_csv(os.path.join(DATA,"ticker_sectors.csv")).set_index("ticker")["sector"].to_dict()
def theme(t):
    if t in CRYPTO: return "암호화폐"
    s=sc.get(t); return KOR.get(s) if isinstance(s,str) else None
THEMES={"기술/반도체":("XLK",["commerce-department","federal-communications-commission"]),
 "금융":("XLF",["treasury-department","securities-and-exchange-commission"]),
 "헬스케어":("XLV",["health-and-human-services-department","food-and-drug-administration"]),
 "에너지":("XLE",["energy-department","environmental-protection-agency"]),
 "산업재":("XLI",["defense-department","transportation-department"]),
 "커뮤니케이션":("XLC",["federal-communications-commission"]),
 "필수소비재":("XLP",["agriculture-department","food-and-drug-administration"]),
 "소재":("XLB",["environmental-protection-agency","interior-department"])}
# 의회 순매수 by 섹터·연도
d=pd.read_csv(os.path.join(DATA,"combined_2019_2026.csv"),parse_dates=["transaction_date"])
d["amount"]=pd.to_numeric(d["amount"],errors="coerce"); d=d.dropna(subset=["amount"])
d["signed"]=np.where(d.type=="P",d.amount,np.where(d.type=="S",-d.amount,0)); d["yr"]=d.transaction_date.dt.year
d["theme"]=d.ticker.map(theme)
nb=d.groupby(["theme","yr"]).signed.sum().div(1e6)
# 규제강도 by 섹터·연도 (Federal Register)
FRc={}
def reg(th,y):
    tot=0
    for a in THEMES[th][1]:
        k=(a,y)
        if k not in FRc:
            j=jget(f"https://www.federalregister.gov/api/v1/documents.json?conditions%5Btype%5D=RULE&conditions%5Bagencies%5D%5B%5D={a}&conditions%5Bpublication_date%5D%5Bgte%5D={y}-01-01&conditions%5Bpublication_date%5D%5Blte%5D={y}-12-31&per_page=1")
            FRc[k]=j.get("count",0); time.sleep(0.08)
        tot+=FRc[k]
    return tot
# 섹터 ETF 연말 → 초과수익
etfs=[v[0] for v in THEMES.values()]
px=yf.download(etfs+["SPY"],start="2019-06-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
ye=px.resample("YE").last(); ye.index=ye.index.year
def sret(etf,y):  # y→y+1 섹터 초과수익(vs SPY)
    if y+1 in ye.index and not pd.isna(ye.loc[y,etf]):
        return ((ye.loc[y+1,etf]/ye.loc[y,etf]-1)-(ye.loc[y+1,"SPY"]/ye.loc[y,"SPY"]-1))*100
    if y==2025: return ((px[etf].dropna().iloc[-1]/ye.loc[2025,etf]-1)-(px["SPY"].dropna().iloc[-1]/ye.loc[2025,"SPY"]-1))*100
    return None
rows=[]
for th,(etf,_) in THEMES.items():
    for y in range(2020,2026):
        f_next=sret(etf,y); f_same=sret(etf,y-1)
        rows.append(dict(theme=th,year=y,netbuy=round(nb.get((th,y),0),1),reg=reg(th,y),
                         fwd_next=f_next,fwd_same=f_same))
p=pd.DataFrame(rows).dropna(subset=["fwd_next"])
print(f"섹터-연도 관측: {len(p)} ({p.theme.nunique()}섹터 × {sorted(p.year.unique())})\n")
print("="*60); print("정책신호 → 섹터 초과수익 (섹터=단위, 중립화 안 함)"); print("="*60)
for col,lab in [("netbuy","의회 순매수"),("reg","규제강도")]:
    rN,pN=pearsonr(p[col],p.fwd_next)        # 선행: 정책 t → 섹터수익 t+1
    sub=p.dropna(subset=["fwd_same"]); rS,pS=pearsonr(sub[col],sub.fwd_same)  # 동행
    print(f"  {lab}: 선행(t→t+1) r={rN:+.2f}(p={pN:.2f}) | 동행(t→t) r={rS:+.2f}(p={pS:.2f})")
print("\n선행>0·유의 → 정책이 섹터 로테이션을 예측(엣지). 동행만 크면 → 이미 반영(엣지 아님).")
# 결합 신호: 순매수+규제 z합
def z(s): return (s-s.mean())/s.std() if s.std()>0 else s*0
p["pol"]=z(p.netbuy)+z(p.reg)
rP,pP=pearsonr(p.pol,p.fwd_next); print(f"\n결합 정책신호 → 익년 섹터초과: r={rP:+.2f} (p={pP:.2f})")
hi=p[p.pol>=p.pol.median()]; lo=p[p.pol<p.pol.median()]
print(f"정책신호 강한 섹터-연도 익년초과 평균 {hi.fwd_next.mean():+.1f}% vs 약한 {lo.fwd_next.mean():+.1f}%")
p.to_csv(os.path.join(DATA,"sector_rotation.csv"),index=False)
