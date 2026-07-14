#!/usr/bin/env python3
"""정책이벤트 패널 — 사인(수혜+/피해-)이 명확한 ~30개 정책이벤트 → 대상 (하위)섹터 사인조정 초과수익 t-검정.
가설: 정책이벤트는 대상 섹터를 '예상 방향'으로 (특히 다년) 움직인다 → 사인조정 CAR 평균>0·유의?
한계: 이벤트 날짜·사인·대상섹터는 판단 개입(주관), 교란(동시 매크로) 잔존, ETF 단위."""
import numpy as np,pandas as pd,yfinance as yf
from scipy.stats import ttest_1samp
# (날짜, 라벨, 대상ETF, 사인)  사인 +1=수혜, -1=피해
EV=[
 ("2022-07-27","CHIPS 상원통과","SMH",+1),("2022-08-09","CHIPS 서명","SMH",+1),
 ("2023-10-30","바이든 AI 행정명령","SMH",+1),("2022-10-07","對中 반도체 수출통제","SMH",-1),
 ("2023-10-17","수출통제 강화","SMH",-1),("2023-08-09","對中 투자제한 EO","SMH",-1),
 ("2021-12-27","NDAA FY22","ITA",+1),("2022-12-23","NDAA FY23","ITA",+1),
 ("2023-12-22","NDAA FY24","ITA",+1),("2024-12-23","NDAA FY25","ITA",+1),
 ("2022-02-24","러시아 우크라 침공","ITA",+1),("2024-04-24","우크라/이스라엘 지원 $95B","ITA",+1),
 ("2022-08-16","IRA 청정에너지","ICLN",+1),("2022-08-16","IRA 태양광","TAN",+1),
 ("2025-01-20","트럼프 에너지 EO(시추)","XLE",+1),("2022-03-31","SPR 방출","XLE",-1),
 ("2022-08-16","IRA 약가인하","IBB",-1),("2023-08-29","메디케어 협상 1차명단","XLV",-1),
 ("2023-03-12","SVB·은행 스트레스","KBE",-1),
 ("2024-01-10","현물 비트코인 ETF 승인","BITO",+1),("2025-01-23","트럼프 크립토 EO","BITO",+1),
 ("2025-03-06","전략적 비트코인 비축 EO","BITO",+1),
 ("2025-04-02","해방의날 관세","SLX",+1),("2025-02-01","캐/멕/중 관세","SLX",+1),
 ("2025-04-02","해방의날 관세(수입원가)","XLK",-1),("2025-04-09","관세 90일 유예","XLK",+1),
 ("2021-11-15","인프라법(IIJA) 서명","XLI",+1),("2021-11-15","IIJA 철강/소재","SLX",+1),
 ("2025-08-22","인텔 정부지분","SMH",+1),
]
T=sorted(set(e[2] for e in EV))+["SPY"]
px=yf.download(T,start="2021-01-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
idx=px.index
def car(tk,date,h):
    if tk not in px: return None
    pos=idx.searchsorted(pd.Timestamp(date))
    if pos>=len(idx): return None
    if h<0: b=max(0,pos+h); e=pos
    elif h is None: b=pos; e=len(idx)-1
    else: b=pos; e=min(pos+h,len(idx)-1)
    s=px[tk]
    if pd.isna(s.iloc[b]) or pd.isna(s.iloc[e]) or b>=e: return None
    return ((s.iloc[e]/s.iloc[b]-1)-(px["SPY"].iloc[e]/px["SPY"].iloc[b]-1))*100
HOR=[("사전[-63d]",-63),("+1m",21),("+3m",63),("+6m",126),("+1y",252)]
print(f"정책이벤트 {len(EV)}개 → 사인조정 대상섹터 초과수익(vs SPY). 평균>0·유의 = 예상방향 효과\n")
print(f"{'호라이즌':<11}{'n':>4}{'평균CAR':>9}{'t값':>7}{'p':>7}{'승률':>7}")
rowsd={}
for lab,h in HOR:
    vals=[]
    for d,_,tk,sg in EV:
        c=car(tk,d,h)
        if c is not None: vals.append(sg*c)   # 사인조정
    a=np.array(vals); t,p=ttest_1samp(a,0)
    rowsd[lab]=a
    print(f"{lab:<11}{len(a):>4}{a.mean():>+9.1f}{t:>+7.2f}{p:>7.3f}{(a>0).mean()*100:>6.0f}%")
# 수혜(+)만 / 카테고리
print("\n수혜이벤트(+)만 +1y:", end=" ")
pos=[car(tk,d,252) for d,_,tk,sg in EV if sg>0]; pos=[v for v in pos if v is not None]
print(f"평균 {np.mean(pos):+.1f}% (n={len(pos)})")
print("피해이벤트(-)만 +1y (원시, 음수기대):", end=" ")
neg=[car(tk,d,252) for d,_,tk,sg in EV if sg<0]; neg=[v for v in neg if v is not None]
print(f"평균 {np.mean(neg):+.1f}% (n={len(neg)})")
