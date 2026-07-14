#!/usr/bin/env python3
"""PM 백테스트 — ① 규제·이해상충 리스크 오버레이 ② 정책촉매 이벤트북 사이징.
①: 고-nexus/로비 종목이 실제로 변동성·드로다운·테일이 큰가(헤지 가치).
②: 바이너리 정책일 [-1,+1] 회피가 SPY 대비 변동성조정 수익을 개선하나."""
import os,re,json,urllib.request,numpy as np,pandas as pd,yfinance as yf
from scipy.stats import pearsonr
DATA=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"data")
d=pd.read_csv(os.path.join(DATA,"combined_2019_2026.csv")); d["amount"]=pd.to_numeric(d["amount"],errors="coerce")
UNIV=[t for t in d.groupby("ticker").amount.sum().sort_values(ascending=False).index if re.match(r'^[A-Z]{1,5}$',t)][:60]
nx=pd.read_csv(os.path.join(DATA,"conflict_nexus.csv"))
conf=nx.groupby("종목").의원.nunique().to_dict()              # 충돌 의원수
lob=pd.read_csv(os.path.join(DATA,"policy_footprint_panel.csv")); lob24=lob[lob.year==2024].set_index("ticker")["lobby"].to_dict()
px=yf.download([t.replace(".","-") for t in UNIV]+["SPY"],start="2022-12-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
def risk(tk):
    s=px[tk.replace(".","-")].dropna(); s=s[s.index>=pd.Timestamp("2023-01-01")]
    if len(s)<100: return None
    r=s.pct_change().dropna(); vol=r.std()*np.sqrt(252)*100
    dd=(s/s.cummax()-1).min()*100; dn=r[r<0].std()*np.sqrt(252)*100
    return vol,dd,dn
rows=[]
for tk in UNIV:
    rk=risk(tk)
    if rk: rows.append(dict(ticker=tk,conf=conf.get(tk,0),lobby=lob24.get(tk,0),vol=rk[0],maxDD=rk[1],downdev=rk[2]))
b=pd.DataFrame(rows)
print("="*60); print("[① 리스크 오버레이] 고-nexus/로비 종목이 테일·DD가 큰가? (n=%d)"%len(b)); print("="*60)
for col,lab in [("conf","충돌의원수"),("lobby","로비$24")]:
    if b[col].std()>0:
        rv=pearsonr(b[col],b.vol); rd=pearsonr(b[col],b.maxDD)
        print(f"  {lab} ↔ 변동성: r={rv[0]:+.2f}(p={rv[1]:.2f}) | ↔ 최대낙폭: r={rd[0]:+.2f}(p={rd[1]:.2f})")
hi=b[b.conf>=b.conf.median()]; lo=b[b.conf<b.conf.median()]
print(f"  충돌의원 많은 종목 평균: 변동성 {hi.vol.mean():.0f}% DD {hi.maxDD.mean():.0f}% | 적은 종목: 변동성 {lo.vol.mean():.0f}% DD {lo.maxDD.mean():.0f}%")
# 관세 충격 윈도(정책 테일): 2025-04-02~04-09
ti=px.index; a=ti.searchsorted(pd.Timestamp("2025-04-02")); z=ti.searchsorted(pd.Timestamp("2025-04-10"))
b["관세窓"]=[ (px[t.replace(".","-")].iloc[z]/px[t.replace(".","-")].iloc[a]-1)*100 if t.replace(".","-") in px else None for t in b.ticker]
hl=b.dropna(subset=["관세窓"])
print(f"  [정책충격 테일] 2025-04 관세窓 수익: 로비高 {hl[hl.lobby>=hl.lobby.median()].관세窓.mean():+.1f}% vs 로비低 {hl[hl.lobby<hl.lobby.median()].관세窓.mean():+.1f}%")

print("\n"+"="*60); print("[② 이벤트북 사이징] 바이너리 정책일 회피가 변동성조정수익 개선?"); print("="*60)
# FOMC (연준 자동) + 정책충격
UA={"User-Agent":"research"}
fomc=[]
try:
    h=urllib.request.urlopen(urllib.request.Request("https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",headers=UA),timeout=20).read().decode("utf-8","ignore")
    for yr,sec in zip(re.findall(r'(20\d\d)\s*FOMC Meetings',h),re.split(r'20\d\d\s*FOMC Meetings',h)[1:]):
        for m,(d1,d2) in zip(re.findall(r'fomc-meeting__month[^>]*>(?:\s*<[^>]+>)*\s*([A-Z][a-z]+)',sec),re.findall(r'fomc-meeting__date[^"]*"[^>]*>\s*(\d+)[-/](\d+)',sec)):
            try: fomc.append(pd.Timestamp(f"{m} {d2} {yr}"))
            except: pass
except: pass
SHOCK=[pd.Timestamp(x) for x in ["2025-04-02","2025-04-09","2022-08-16","2025-08-22","2023-03-10"]]
spy=px["SPY"].dropna(); r=spy.pct_change().dropna()
def stats(ret):
    c=(1+ret).prod()-1; v=ret.std()*np.sqrt(252); sh=(ret.mean()*252)/v if v>0 else 0
    dd=((1+ret).cumprod()/(1+ret).cumprod().cummax()-1).min()
    return c*100,v*100,sh,dd*100
def avoid(events,win=1):
    mask=pd.Series(True,index=r.index)
    for e in events:
        for off in range(-win,win+1):
            pos=r.index.searchsorted(e)+off
            if 0<=pos<len(r.index): mask.iloc[pos]=False
    return r.where(mask,0.0)
bh=stats(r)
print(f"  {'전략':<22}{'수익%':>8}{'변동성%':>8}{'Sharpe':>8}{'MaxDD%':>8}")
print(f"  {'SPY 매수보유':<20}{bh[0]:>8.0f}{bh[1]:>8.1f}{bh[2]:>8.2f}{bh[3]:>8.0f}")
for lab,ev in [("FOMC窓 회피",fomc),("정책충격窓 회피",SHOCK),("FOMC+충격 회피",fomc+SHOCK)]:
    s=stats(avoid(ev))
    print(f"  {lab:<20}{s[0]:>8.0f}{s[1]:>8.1f}{s[2]:>8.2f}{s[3]:>8.0f}  (회피일 {sum(1 for e in ev if r.index[0]<=e<=r.index[-1])*3})")
