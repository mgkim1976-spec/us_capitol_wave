#!/usr/bin/env python3
"""NANC/GOP/SPY 리스크·수익 종합 지표 + 드로다운 + 월별 + 보유/섹터.
출력은 data/ 에 CSV 저장. 무위험수익률은 ^IRX(13주 T-bill) 평균 사용."""
import os, json
import numpy as np, pandas as pd, yfinance as yf

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data"); os.makedirs(DATA, exist_ok=True)
T = ["NANC","GOP","SPY"]; SPLIT="2025-01-17"

px = yf.download(T, start="2023-02-01", end="2026-05-26", auto_adjust=True, progress=False)["Close"].dropna(how="all")
# risk-free
irx = yf.download("^IRX", start="2023-02-01", end="2026-05-26", auto_adjust=True, progress=False)["Close"].dropna()
rf_ann = float(irx.mean())/100.0  # ^IRX in percent
rf_d = rf_ann/252
ret = px.pct_change().dropna()

def mdd(s):
    s=s.dropna(); peak=s.cummax(); dd=s/peak-1; 
    return float(dd.min()*100), dd.idxmin().date(), peak[:dd.idxmin()].idxmax().date()

def metrics(sub_ret, sub_px):
    out={}
    for t in T:
        r=sub_ret[t].dropna()
        if len(r)<5: out[t]={}; continue
        ann_ret=(1+ (sub_px[t].dropna().iloc[-1]/sub_px[t].dropna().iloc[0]-1))**(252/len(r))-1
        vol=r.std()*np.sqrt(252)
        downside=r[r<0].std()*np.sqrt(252)
        sharpe=(r.mean()*252-rf_ann)/vol if vol>0 else np.nan
        sortino=(r.mean()*252-rf_ann)/downside if downside>0 else np.nan
        d,dt,pk=mdd(sub_px[t])
        # beta/corr vs SPY
        m=pd.concat([r, sub_ret["SPY"]],axis=1).dropna(); m.columns=["x","spy"]
        beta=np.polyfit(m["spy"],m["x"],1)[0] if len(m)>5 else np.nan
        corr=m["x"].corr(m["spy"])
        out[t]=dict(CAGR=round(ann_ret*100,2),Vol=round(vol*100,2),
                    Sharpe=round(sharpe,2),Sortino=round(sortino,2),
                    MDD=round(d,2),beta_SPY=round(beta,2),corr_SPY=round(corr,2))
    return out

eras={"바이든":(None,SPLIT),"트럼프2기":(SPLIT,None),"전체":(None,None)}
allm={}
for name,(s,e) in eras.items():
    rr=ret.copy(); pp=px.copy()
    if s: rr=rr[rr.index>=pd.Timestamp(s)]; pp=pp[pp.index>=pd.Timestamp(s)]
    if e: rr=rr[rr.index<=pd.Timestamp(e)]; pp=pp[pp.index<=pd.Timestamp(e)]
    allm[name]=metrics(rr,pp)
print(f"무위험수익률(rf, ^IRX 평균 연율): {rf_ann*100:.2f}%\n")
for name in eras:
    print(f"=== [{name}] ===")
    print(pd.DataFrame(allm[name]).T.to_string()); print()

# NANC-GOP correlation by era
print("=== NANC-GOP 일간수익률 상관 ===")
for name,(s,e) in eras.items():
    rr=ret.copy()
    if s: rr=rr[rr.index>=pd.Timestamp(s)]
    if e: rr=rr[rr.index<=pd.Timestamp(e)]
    print(f"  {name}: {rr['NANC'].corr(rr['GOP']):.3f}")
print()

# Up/Down capture vs SPY (full period)
print("=== SPY 대비 업/다운 캡처 (전체기간) ===")
up=ret[ret["SPY"]>0]; dn=ret[ret["SPY"]<0]
for t in ["NANC","GOP"]:
    uc=(up[t].mean()/up["SPY"].mean())*100
    dc=(dn[t].mean()/dn["SPY"].mean())*100
    print(f"  {t}: 상승장 캡처 {uc:.0f}%, 하락장 캡처 {dc:.0f}%")
print()

# Top drawdown episodes (full)
print("=== 최대낙폭 구간 (전체) ===")
for t in T:
    d,dt,pk=mdd(px[t]); print(f"  {t}: {d:.1f}%  (고점 {pk} → 저점 {dt})")
print()

# Monthly returns
print("=== 월별 총수익률 % ===")
mret=(px.resample("ME").last().pct_change()*100).round(2)
mret.index=mret.index.to_period("M").astype(str)
print(mret.dropna(how="all").to_string())
mret.to_csv(os.path.join(DATA,"monthly_returns.csv"))

# save metrics json
with open(os.path.join(DATA,"risk_metrics.json"),"w") as f:
    json.dump({"rf_ann":rf_ann,"eras":allm},f,ensure_ascii=False,indent=2)

# sector & holdings
sec={}; hold={}
for t in ["NANC","GOP"]:
    fd=yf.Ticker(t).funds_data
    sec[t]=fd.sector_weightings
    hold[t]=fd.top_holdings
pd.DataFrame(sec).to_csv(os.path.join(DATA,"sector_weights.csv"))
print("\n저장 완료: data/ (risk_metrics.json, monthly_returns.csv, sector_weights.csv)")
