#!/usr/bin/env python3
"""모자이크 패널 검정 — 5개 층이 익년 초과수익을 예측하나? 풀링·연도별·정권별·다변량.
다중검정 보정·정직한 해석 포함."""
import os,numpy as np,pandas as pd
from scipy.stats import pearsonr
import statsmodels.api as sm
HERE=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); DATA=os.path.join(HERE,"data")
p=pd.read_csv(os.path.join(DATA,"mosaic_panel.csv"))
p=p.sort_values(["ticker","year"])
p["lobbyD"]=p.groupby("ticker")["lobby"].diff().fillna(0)   # 로비 증가분
LAYERS={"lobby":"로비$","lobbyD":"로비증가","contracts":"연방계약$","netbuy":"의회순매수$","members":"거래의원수","cmt_trades":"관할위원거래","reg":"규제강도"}
print(f"패널: {len(p)} obs, {p.ticker.nunique()}종목 × {sorted(p.year.unique())}\n")
print("="*64); print("[1] 풀링 상관 (각 층 ↔ 익년 초과수익)"); print("="*64)
res=[]
for c,lab in LAYERS.items():
    x=p[c].fillna(0)
    if x.std()==0: print(f"  {lab}: (변동없음)"); continue
    r,pv=pearsonr(x,p.fwd_exc); res.append((lab,r,pv))
    print(f"  {lab:12}: r={r:+.2f}  p={pv:.3f}  {'*유의' if pv<0.05 else ''}")
print(f"  [다중검정] {len(res)}개 변수 → Bonferroni 임계 p<{0.05/len(res):.3f}")

print("\n"+"="*64); print("[2] 연도별 robustness (netbuy·lobby ↔ 익년 초과수익)"); print("="*64)
for y in sorted(p.year.unique()):
    s=p[p.year==y]
    if len(s)<6: continue
    rn=pearsonr(s.netbuy,s.fwd_exc)[0]; rl=pearsonr(s.lobby,s.fwd_exc)[0] if s.lobby.std()>0 else float('nan')
    print(f"  {y}→{y+1}: netbuy r={rn:+.2f}, lobby r={rl:+.2f}  (n={len(s)})")

print("\n"+"="*64); print("[3] 정권별 (익년수익 기준: ~2024=바이든, 2025~=트럼프2기)"); print("="*64)
for lab,mask in [("바이든기(y<=2023)",p.year<=2023),("전환·트럼프2기(y>=2024)",p.year>=2024)]:
    s=p[mask]
    for c in ["netbuy","lobby","contracts"]:
        if s[c].std()>0:
            r,pv=pearsonr(s[c],s.fwd_exc); print(f"  {lab} {LAYERS[c]}: r={r:+.2f} (p={pv:.2f}, n={len(s)})")
    print()

print("="*64); print("[4] 다변량 회귀 (모든 층 동시통제, 표준화)"); print("="*64)
X=p[list(LAYERS)].fillna(0); X=(X-X.mean())/X.replace(0,np.nan).std().fillna(1)
X=X.fillna(0); X=sm.add_constant(X); m=sm.OLS(p.fwd_exc,X).fit()
for c in LAYERS:
    print(f"  {LAYERS[c]:12}: β={m.params.get(c,0):+.2f}  t={m.tvalues.get(c,0):+.2f}  {'*' if abs(m.tvalues.get(c,0))>2 else ''}")
print(f"  R²={m.rsquared:.2f}, n={int(m.nobs)}")

print("\n"+"="*64); print("[5] 모자이크 종합점수 → 분위 검정"); print("="*64)
def z(s): return (s-s.mean())/s.std() if s.std()>0 else s*0
p["mosaic"]=z(np.log1p(p.lobby))+z(p.lobbyD)+z(np.log1p(p.contracts))+z(p.netbuy)+z(p.cmt_trades)
q=p.mosaic.quantile([.25,.75])
hi=p[p.mosaic>=q[.75]]; lo=p[p.mosaic<=q[.25]]
print(f"  상위25% 익년초과 평균 {hi.fwd_exc.mean():+.1f}% (n={len(hi)}) vs 하위25% {lo.fwd_exc.mean():+.1f}% (n={len(lo)})")
rm,pm=pearsonr(p.mosaic,p.fwd_exc); print(f"  모자이크점수 ↔ 익년초과: r={rm:+.2f} (p={pm:.3f})")
