# Capitol Wave — 미 의회 의원 거래·NANC/GOP ETF 소진적 검증

미 상·하원 의원의 주식거래 신고(STOCK Act)와 이를 추종하는 두 ETF(**NANC** 민주 추종 / **GOP** 공화 추종)에, "의원을 따라 사면 이길 수 있는가"라는 통념을 **공개 데이터로 갈 수 있는 끝까지** 검증한 프로젝트입니다.

## 결론: 어느 층위에서도 거래 가능한 알파는 없다

검증은 알파를 찾지 못했습니다. 그리고 그 **못 찾음 자체가 이 저장소의 결과물**입니다.

| 층위 | 검증 결과 |
|---|---|
| 의원 추종 | 신고가 stale(중위 **28일**, 17%는 45일 초과). 실제 **거래일에 사도** SPY 미달 — 승률 43~49%, 전 구간 t<2 |
| 위원 실력 | 지속성 0 (2024↔2025 위원별 성과 상관 −0.06~−0.14). 상위 위원 = 소수 홈런 + AI 베타 |
| ETF 성과 | NANC 우위(+16.7%p)는 **섹터 배분효과로 과설명**, 종목선택은 오히려 열위. 섹터중립 알파 전부 t<2 |
| "여당 ETF가 이긴다" | **반복되지 않음.** 트럼프 1기엔 여당(공화) 모방포트가 대패(+15% vs SPY +83%). 여당 우위는 *민주당 포트의 구조적 테크 편향이 AI붐과 겹친 우연* |
| 로비 | *정책*에는 보상되나(IRA 약가인하 실제 희석) *주가 알파*로는 종목·섹터·섹터내 어디서도 안 잡힘 — 로비강도 = 가치-incumbent 프록시 |
| 정책→섹터 | 메커니즘은 실재하나(CHIPS→반도체 +324%, 관세→철강 +41%) 효율적으로 가격됨(동행≠선행), 광범위 표본에선 통계 미확증 |

> **NANC·GOP는 "의원 정보"라는 마케팅을 입은 AI 베타 상품이다.** 이 데이터의 가치는 알파가 아니라 **맥락과 거버넌스 투명성**에 있다.
>
> 진짜 선행 엣지는 정책을 *미리* 아는 사적 정치정보(로비스트→기관) 채널이며, STOCK Act가 의원은 공시시키고 정치정보 산업은 등록 조항을 삭제해 풀어준 그 틈에 — **공개 데이터 밖에** 남아 있습니다.

전체 검증 과정은 **[REPORT_FINAL.md](REPORT_FINAL.md)** 참고 (성과 → 귀속 → 신고 → 복제 → 모자이크 → 정책이벤트 → 로비 2단계).

## 방법론 원칙

- **팩트(F)와 가정/해석(A) 등급 분리** — 결론을 좌우하는 가정은 단정하지 않고 라벨을 답니다.
- 모든 알파 주장은 **t값·다중검정·사인조정·섹터/팩터 통제**로 검증하고, 표본 한계를 명시합니다.
- 사후관점(hindsight)·n=1 패턴은 "패턴 예시"로만 제시합니다. (예: 정권매칭 전략 +112% → §9.5에서 정권을 더 넣자 반복 실패)

## 데이터 소스 (전부 공개·대부분 API 키 불요)

| 소스 | 용도 | 비고 |
|---|---|---|
| House Clerk PTR | 하원 거래신고 | PDF 파싱 |
| Senate eFD | 상원 거래신고 | `curl_cffi` TLS 지문 우회 필요 |
| SEC N-PORT | NANC/GOP 전체 보유 | CIK 1742912 |
| Senate LDA | 로비 지출 | 키 불요 |
| USASpending / Federal Register | 연방계약 / 규제 | 키 불요 |
| yfinance / congress-legislators | 가격 / 의원-정당 매핑 | |

거래 데이터 **22,190건 (2019~2026)** 이 `data/`에 CSV로 포함되어 있습니다.

## 구성

```
REPORT_FINAL.md          통합 최종 보고서 (핵심)
REPORT.md, REPORT_PART2/3.md, NANC_GOP_종합보고서.md   초기 분석판
MOSAIC_LAYERS.md         5층 정치정보 모자이크 설계
HEDGE_FUND_PLAYBOOK.md   기관 관점 정리
dashboard/capitol_wave.html   Capitol Wave 대시보드 (정책 플레이북·N-PORT 보유변화·정책캘린더)
scripts/                 수집·분석 스크립트 40여 개
data/                    거래·로비·가격 데이터 CSV
```

## 실행

```bash
pip install pandas numpy yfinance requests curl_cffi beautifulsoup4 statsmodels
cp .env.example .env      # SEC_USER_AGENT를 본인 이메일로 채울 것 (SEC 요구사항)

python3 scripts/congress_ptr_pipeline.py   # 하원 PTR
python3 scripts/senate_ptr_pipeline.py     # 상원 eFD
python3 scripts/exposure_timing.py         # 통합·플로우
python3 scripts/policy_radar_dashboard.py  # 대시보드 재생성

./scripts/run_monthly.sh                   # 위 파이프라인 월간 일괄 실행
```

## ⚠️ 면책

**대시보드는 매매신호가 아닙니다.** 이 프로젝트의 명시적 결론은 "여기서 거래 가능한 알파를 찾지 못했다"이며, 산출물은 정책·테마의 **맥락 파악용**입니다. 투자 권유가 아니며, 개인 연구·학습 목적입니다. 데이터·분석의 정확성을 보증하지 않습니다.

## 라이선스

MIT
