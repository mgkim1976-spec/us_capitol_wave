import os
#!/usr/bin/env python3
"""섹터 내 헤비 vs 라이트 로비 — 약가인하(IRA) 후, 헬스케어 섹터 내에서 로비강한 제약사가 더 버텼나?
섹터(XLV) 대비 초과수익으로 측정 → AI 섹터로테이션 제거, 순수 '로비가 개별주 방어하나' 검정.
로비 2022-2024 합(약가인하 싸움기) → forward 2023-01~2026-05, vs XLV(섹터중립) & SPY."""
import urllib.request,urllib.parse,json,time,numpy as np,pandas as pd,yfinance as yf
from scipy.stats import pearsonr
UA={"User-Agent": os.environ.get("SEC_USER_AGENT", "research your-email@example.com")}
PH=["PFE","MRK","JNJ","ABBV","LLY","BMY","AMGN","GILD","REGN","VRTX","BIIB","MRNA","ZTS","JAZZ","NBIX","INCY","ALNY","SRPT","BMRN","HALO","TEVA","VTRS","UTHR"]
def lob(c):
    t=0
    for y in (2022,2023,2024):
        url=f"https://lda.senate.gov/api/v1/filings/?client_name={urllib.parse.quote(c)}&filing_year={y}&page_size=25";h=0
        while url and h<4:
            try:j=json.loads(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=25).read())
            except:break
            if "results" not in j:break
            for f in j["results"]:
                try:t+=float(f.get("income") or f.get("expenses") or 0)
                except:pass
            url=j.get("next");h+=1;time.sleep(0.07)
    return t
px=yf.download(PH+["XLV","SPY"],start="2022-12-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
S=px.index[px.index.searchsorted(pd.Timestamp("2023-01-03"))]
xlv=px["XLV"].iloc[-1]/px["XLV"].loc[S]-1; spy=px["SPY"].iloc[-1]/px["SPY"].loc[S]-1
rows=[]
for tk in PH:
    try: nm=yf.Ticker(tk).info.get("shortName") or tk; mc=yf.Ticker(tk).info.get("marketCap")
    except: nm,mc=tk,None
    cl=nm.split(",")[0]
    for s in [" Inc"," Corporation"," Corp"," Co"," Ltd"," plc"," Company"," Holdings"," Pharmaceuticals"," Therapeutics"," Pharma"]: cl=cl.replace(s," ")
    cl=cl.strip()
    if tk not in px or pd.isna(px[tk].loc[S]): continue
    r=(px[tk].iloc[-1]/px[tk].loc[S]-1)*100
    L=lob(cl)
    rows.append(dict(ticker=tk,client=cl,lobby_3y=round(L/1e6,1),mc=mc,intensity=(L/mc*1e6) if mc else None,
                     vs_XLV=round(r-xlv*100,1),vs_SPY=round(r-spy*100,1)))
    print(f"{tk} lob3y=${L/1e6:.1f}M vsXLV={r-xlv*100:+.0f}%")
df=pd.DataFrame(rows); df.to_csv("data/within_sector_lobby.csv",index=False)
print(f"\n섹터(XLV) 동기간 vs SPY: {xlv*100-spy*100:+.0f}%p (헬스케어가 시장을 {xlv*100-spy*100:+.0f}%p)")
print(f"표본 {len(df)} 제약/바이오\n")
d2=df.dropna(subset=["intensity"])
for col,lab in [("lobby_3y","로비$"),("intensity","로비강도(/시총)")]:
    r,p=pearsonr(d2[col],d2.vs_XLV); print(f"  {lab} ↔ 섹터(XLV)대비 초과: r={r:+.2f} (p={p:.2f}, n={len(d2)})")
for col,lab in [("lobby_3y","로비$"),("intensity","로비강도")]:
    med=d2[col].median(); hi=d2[d2[col]>=med]; lo=d2[d2[col]<med]
    print(f"  [{lab}] 헤비 섹터대비 {hi.vs_XLV.mean():+.1f}% vs 라이트 {lo.vs_XLV.mean():+.1f}%")
