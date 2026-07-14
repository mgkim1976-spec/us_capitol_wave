#!/usr/bin/env python3
"""로비 효과 재측정 — 측정방식 수정판.
기존 오류: ①1년 창(너무 짧음) ②주가초과수익만(정책결과·ROI·방어효과 무시) ③횡단면 상관(포트폴리오 아님)
          ④의회거래 24종목(전부 헤비로비어, 대조 없음) ⑤사이즈 미보정.
수정: 광범위 유니버스(~55 대형주, 로비 편차 큼) × 장기(3.4년 forward) × 포트폴리오(헤비 vs 라이트) × 강도(로비/시총) 정규화.
로비 2020-2022 → forward 2023-01~2026-05 (완전 out-of-sample)."""
import os,json,time,urllib.request,urllib.parse,numpy as np,pandas as pd,yfinance as yf
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
UA={"User-Agent": os.environ.get("SEC_USER_AGENT", "research your-email@example.com")}
def jget(u):
    try: return json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30).read())
    except Exception: return {}
UNIV=["AAPL","MSFT","GOOGL","AMZN","META","NVDA","AVGO","ORCL","CRM","ADBE","INTC","CSCO","QCOM","AMD","TXN",
 "T","VZ","CMCSA","DIS","NFLX","JNJ","PFE","MRK","ABBV","LLY","UNH","TMO","ABT","JPM","BAC","GS","MS","WFC",
 "C","BLK","V","MA","AXP","XOM","CVX","COP","SLB","LMT","RTX","NOC","GD","BA","CAT","DE","HON","UPS","PG","KO",
 "PEP","WMT","COST","HD","MCD","NKE","SBUX"]
def lobby(client):  # 2020-2022 합
    t=0
    for y in (2020,2021,2022):
        url=f"https://lda.senate.gov/api/v1/filings/?client_name={urllib.parse.quote(client)}&filing_year={y}&page_size=25";h=0
        while url and h<5:
            j=jget(url)
            if "results" not in j: break
            for f in j["results"]:
                try:t+=float(f.get("income") or f.get("expenses") or 0)
                except:pass
            url=j.get("next");h+=1;time.sleep(0.08)
    return t
# 가격·시총
px=yf.download(UNIV+["SPY"],start="2022-12-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
START=px.index[px.index.searchsorted(pd.Timestamp("2023-01-03"))]
spy_ret=px["SPY"].iloc[-1]/px["SPY"].loc[START]-1
rows=[]
for tk in UNIV:
    try:
        info=yf.Ticker(tk).info; nm=info.get("shortName") or tk; mc=info.get("marketCap")
    except: nm,mc=tk,None
    cl=nm.split(",")[0]
    for s in [" Inc"," Corporation"," Corp"," Co"," Ltd"," plc"," Company"," Holdings"," Group"," Platforms","."]: cl=cl.replace(s," ")
    cl=cl.strip()
    lob=lobby(cl)
    if tk not in px or pd.isna(px[tk].loc[START]): continue
    fwd=(px[tk].iloc[-1]/px[tk].loc[START]-1)*100
    rows.append(dict(ticker=tk,client=cl,lobby_3y=lob,marketcap=mc,intensity=(lob/mc*1e6) if mc else None,fwd_ret=round(fwd,1),exc=round(fwd-spy_ret*100,1)))
    print(f"{tk} lob3y=${lob/1e6:.1f}M exc={fwd-spy_ret*100:+.0f}%")
df=pd.DataFrame(rows); df.to_csv(os.path.join(DATA,"lobby_portfolio.csv"),index=False)
print(f"\n저장 {len(df)}종목 → data/lobby_portfolio.csv  (SPY 동기간 +{spy_ret*100:.0f}%)")
