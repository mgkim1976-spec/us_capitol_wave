#!/usr/bin/env python3
"""GOP 잔차의 종목단위 분해 — '간접 AI 베타' 가설 검증.
트럼프기(2025-01-17~) GOP 상위보유 각 종목의:
  A) GOP 초과수익(vs SPY) 기여도 = w*(r_i - r_SPY)  [현재비중 + 등가중 둘 다]
  B) AI/반도체 팩터 베타: r_i ~ SPY + (SMH-SPY)  → 'AI 인프라' 성격 정량화
한계: 현재비중 스냅샷(액티브펀드라 비중 드리프트=승자 과대반영) → 등가중도 병기해 강건성 확인. top10≈펀드 38%."""
import numpy as np, pandas as pd, yfinance as yf, statsmodels.api as sm
SPLIT="2025-01-17"
# GOP 현재 상위10 (yfinance 검증) + 분류
HOLD={"FIX":(8.8,"AI인프라(데이터센터 냉방/기계)"),"INTC":(6.6,"반도체"),"JPM":(4.1,"금융(정책)"),
      "IBIT":(3.7,"암호화폐(정책)"),"ANET":(3.3,"AI인프라(네트워킹)"),"NVDA":(3.2,"반도체"),
      "UTHR":(2.3,"헬스케어"),"T":(2.0,"통신(방어)"),"AMD":(2.0,"반도체"),"ALL":(1.9,"금융(보험)")}
tks=list(HOLD)+["SPY","SMH"]
px=yf.download(tks,start="2024-06-01",end="2026-05-26",auto_adjust=True,progress=False)["Close"]
tr=px[px.index>=pd.Timestamp(SPLIT)]
def cum(s): s=s.dropna(); return (s.iloc[-1]/s.iloc[0]-1)*100
spy=cum(tr["SPY"])
print(f"트럼프기 SPY: {spy:+.1f}%\n")
wsum=sum(w for w,_ in HOLD.values())
rows=[]
for t,(w,cls) in HOLD.items():
    r=cum(tr[t]); ex=r-spy
    rows.append(dict(ticker=t, 분류=cls, 비중=w, 종목수익=round(r,1), 초과vsSPY=round(ex,1),
                     기여_현재비중=round(w/100*ex,2), 기여_등가중=round((1/len(HOLD))*ex,2)))
df=pd.DataFrame(rows).sort_values("기여_현재비중",ascending=False)
pd.set_option("display.width",160)
print("=== A) 트럼프기 GOP 초과수익(vs SPY) 종목별 기여도 (%p) ===")
print(df.to_string(index=False))
print(f"\n  top10 합계 기여: 현재비중 {df.기여_현재비중.sum():+.1f}%p | 등가중 {df.기여_등가중.sum():+.1f}%p")
# AI인프라/반도체 vs 나머지
ai=df[df.분류.str.contains("AI인프라|반도체")]
oth=df[~df.분류.str.contains("AI인프라|반도체")]
print(f"  AI인프라+반도체 5종목 기여: 현재 {ai.기여_현재비중.sum():+.1f}%p / 등가 {ai.기여_등가중.sum():+.1f}%p")
print(f"  나머지(금융·헬스·통신) 5종목: 현재 {oth.기여_현재비중.sum():+.1f}%p / 등가 {oth.기여_등가중.sum():+.1f}%p")

print("\n=== B) 각 종목의 AI/반도체 팩터 베타  r_i ~ SPY + (SMH-SPY) ===")
ret=px.pct_change().dropna(); ret=ret[ret.index>=pd.Timestamp(SPLIT)]
semis=ret["SMH"]-ret["SPY"]
X=sm.add_constant(pd.DataFrame({"SPY":ret["SPY"],"AI(SMH-SPY)":semis}))
print(f"{'종목':<6}{'분류':<26}{'시장β':>7}{'AIβ':>8}{'R²':>7}")
for t,(w,cls) in HOLD.items():
    m=sm.OLS(ret[t],X).fit()
    star="*" if abs(m.tvalues["AI(SMH-SPY)"])>2 else " "
    print(f"{t:<6}{cls:<26}{m.params['SPY']:>7.2f}{m.params['AI(SMH-SPY)']:>+7.2f}{star}{m.rsquared:>7.2f}")
print("\n(AIβ>0 & 유의(*) = 수익이 AI/반도체 사이클에 동조 → '간접 AI 베타')")
