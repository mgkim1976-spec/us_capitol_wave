#!/usr/bin/env python3
"""분석1: 섹터중립화 분해 (Returns-Based Style Analysis + 갭 귀속).
- 11개 SPDR 섹터 ETF에 대한 수익률기반 회귀로 NANC/GOP 유효 섹터노출 추정
- 제약 RBSA(롱온리·풀투자: w>=0, sum=1)로 '섹터복제 포트폴리오' 구성
- 잔차(actual-replica) = 종목선택/타이밍 알파
- NANC-GOP 누적 성과차를 [배분효과(섹터)] vs [종목선택]으로 분해
한계: yfinance는 역사적 보유를 안 줘서 '유효노출'은 수익률기반 추정(스냅샷 아님). 정권별 윈도로 추정해 로테이션 일부 반영."""
import os, json, numpy as np, pandas as pd, yfinance as yf
import statsmodels.api as sm
from scipy.optimize import minimize

HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA=os.path.join(HERE,"data"); os.makedirs(DATA,exist_ok=True)
SECT={"XLK":"기술","XLC":"커뮤니케이션","XLY":"경기소비재","XLP":"필수소비재","XLE":"에너지",
      "XLF":"금융","XLV":"헬스케어","XLI":"산업재","XLB":"소재","XLRE":"부동산","XLU":"유틸리티"}
SECTORS=list(SECT.keys()); FUNDS=["NANC","GOP","SPY"]; SPLIT="2025-01-17"
ALL=FUNDS+SECTORS
px=yf.download(ALL,start="2023-02-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"].dropna()
ret=px.pct_change().dropna()

def window(r,s,e):
    if s: r=r[r.index>=pd.Timestamp(s)]
    if e: r=r[r.index<=pd.Timestamp(e)]
    return r

def rbsa_weights(y,X):
    """롱온리 풀투자 제약 회귀 (Sharpe 1992)."""
    n=X.shape[1]; A=X.values; b=y.values
    def obj(w): res=b-A@w; return res@res
    cons=({"type":"eq","fun":lambda w:w.sum()-1},)
    bnds=[(0,1)]*n
    w0=np.repeat(1/n,n)
    r=minimize(obj,w0,method="SLSQP",bounds=bnds,constraints=cons,
               options={"maxiter":1000,"ftol":1e-12})
    return pd.Series(r.x,index=X.columns)

def ann(daily_cum_series):
    return daily_cum_series

eras={"바이든":(None,SPLIT),"트럼프2기":(SPLIT,None),"전체":(None,None)}
results={}
for ename,(s,e) in eras.items():
    rw=window(ret,s,e)
    X=rw[SECTORS]
    rec={}
    replica_cum={}; actual_cum={}
    for f in FUNDS:
        y=rw[f]
        # (a) 제약 RBSA -> 유효 섹터노출
        w=rbsa_weights(y,X)
        replica_daily=(X*w).sum(axis=1)
        rep_cum=(1+replica_daily).prod()-1
        act_cum=(1+y).prod()-1
        # (b) 비제약 OLS -> 섹터중립 알파
        Xc=sm.add_constant(X)
        m=sm.OLS(y,Xc).fit()
        a_daily=m.params["const"]; a_ann=((1+a_daily)**252-1)*100
        t_alpha=m.tvalues["const"]; r2=m.rsquared
        rec[f]=dict(weights=w, replica_cum=rep_cum*100, actual_cum=act_cum*100,
                    selection=(act_cum-rep_cum)*100, alpha_ann=a_ann, t_alpha=t_alpha, r2=r2)
        replica_cum[f]=rep_cum; actual_cum[f]=act_cum
    # 갭 귀속 (NANC-GOP)
    gap=(actual_cum["NANC"]-actual_cum["GOP"])*100
    alloc=(replica_cum["NANC"]-replica_cum["GOP"])*100
    selec=((actual_cum["NANC"]-replica_cum["NANC"])-(actual_cum["GOP"]-replica_cum["GOP"]))*100
    rec["_gap"]=dict(total=gap, allocation=alloc, selection=selec)
    results[ename]=rec

# 출력
pd.set_option("display.width",140)
for ename in eras:
    print("="*70); print(f"[{ename}]")
    rec=results[ename]
    # 유효 섹터노출 표
    wdf=pd.DataFrame({f:rec[f]["weights"] for f in FUNDS})*100
    wdf.index=[SECT[i] for i in wdf.index]
    wdf=wdf.round(1)
    print("\n유효 섹터노출 % (제약 RBSA):")
    print(wdf.to_string())
    print("\n섹터중립 알파(연율) / t값 / R²:")
    for f in FUNDS:
        print(f"  {f}: alpha {rec[f]['alpha_ann']:+.2f}%  (t={rec[f]['t_alpha']:.2f})  R²={rec[f]['r2']:.3f}")
    g=rec["_gap"]
    print(f"\nNANC-GOP 성과차 분해:  총 {g['total']:+.1f}%p = 배분효과(섹터) {g['allocation']:+.1f}%p + 종목선택 {g['selection']:+.1f}%p")
    print(f"  → 섹터로 설명되는 비중: {g['allocation']/g['total']*100:.0f}%  / 종목선택: {g['selection']/g['total']*100:.0f}%")
    print()

# 저장
save={}
for ename in eras:
    rec=results[ename]
    save[ename]={f:{"weights":{k:round(v*100,2) for k,v in rec[f]["weights"].items()},
                    "alpha_ann":round(rec[f]["alpha_ann"],2),"t_alpha":round(rec[f]["t_alpha"],2),
                    "r2":round(rec[f]["r2"],3),"replica_cum":round(rec[f]["replica_cum"],2),
                    "actual_cum":round(rec[f]["actual_cum"],2),"selection":round(rec[f]["selection"],2)} for f in FUNDS}
    save[ename]["gap"]={k:round(v,2) for k,v in rec["_gap"].items()}
with open(os.path.join(DATA,"sector_neutral.json"),"w") as fp:
    json.dump(save,fp,ensure_ascii=False,indent=2)
print("저장: data/sector_neutral.json")
