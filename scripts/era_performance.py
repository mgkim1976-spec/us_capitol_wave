#!/usr/bin/env python3
"""
NANC(민주당 의원 거래 추종) vs GOP(공화당 의원 거래 추종) ETF를
미국 집권당(대통령) 구간별로 분석.

- 데이터: yfinance, auto_adjust=True (배당 재투자 반영 조정종가 = 총수익률 근사)
- 구간 분리: 트럼프 2기 취임 2025-01-20 (시장 휴장, 직전 거래일 2025-01-17 종가를 경계로 사용)
- 벤치마크: SPY
- 후속 분석(정책/편입종목)을 위해 가격·결과를 data/ 에 CSV로 저장.

사용: python3 scripts/era_performance.py
"""
import os
import yfinance as yf
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

TICKERS = ["NANC", "GOP", "SPY"]
SPLIT = "2025-01-17"  # 트럼프 2기 취임(1/20) 직전 마지막 거래일
START = "2023-02-01"
END = "2026-05-26"


def fetch():
    data = yf.download(TICKERS, start=START, end=END, auto_adjust=True, progress=False)
    close = data["Close"].dropna(how="all")
    close.to_csv(os.path.join(DATA, "adj_close.csv"))
    return close


def ret(s, start=None, end=None):
    s = s.dropna()
    if start:
        s = s[s.index >= pd.Timestamp(start)]
    if end:
        s = s[s.index <= pd.Timestamp(end)]
    if len(s) < 2:
        return None
    r = (s.iloc[-1] / s.iloc[0] - 1) * 100
    days = (s.index[-1] - s.index[0]).days
    ann = ((1 + r / 100) ** (365 / days) - 1) * 100
    return dict(ret=r, d0=s.index[0].date(), d1=s.index[-1].date(), days=days, ann=ann)


def main():
    close = fetch()
    rows = []
    eras = {
        "바이든(상장~취임직전)": dict(end=SPLIT),
        "트럼프2기(취임~현재)": dict(start=SPLIT),
        "상장이후전체": dict(),
    }
    for era, kw in eras.items():
        for t in TICKERS:
            r = ret(close[t], **kw)
            rows.append(dict(era=era, ticker=t, **r))
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(DATA, "era_returns.csv"), index=False)

    pd.set_option("display.width", 120)
    print(out.round(2).to_string(index=False))

    # 연도별
    yr = {}
    for t in TICKERS:
        s = close[t].dropna()
        row = {}
        for y in [2023, 2024, 2025, 2026]:
            sy = s[s.index.year == y]
            if len(sy) < 2:
                row[y] = None
                continue
            prev = s[s.index < pd.Timestamp(f"{y}-01-01")]
            base = prev.iloc[-1] if len(prev) else sy.iloc[0]
            row[y] = round((sy.iloc[-1] / base - 1) * 100, 2)
        yr[t] = row
    ydf = pd.DataFrame(yr).T
    ydf.to_csv(os.path.join(DATA, "yearly_returns.csv"))
    print("\n연도별(캘린더) 총수익률 %  (2023=상장2/7부터, 2026=YTD)")
    print(ydf.to_string())


if __name__ == "__main__":
    main()
