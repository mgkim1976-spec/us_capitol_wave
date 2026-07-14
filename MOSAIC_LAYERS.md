# 정책정보 모자이크 — 6층 공개 발자국 체계 정리

> **원리:** 로비스트→기관으로 가는 *사적 정책정보*는 비관측이나, 그 정보가 작동하면 **여러 공개 데이터에 시차를 두고 발자국**을 남긴다. 개별 조각은 무해(non-material)하나 **조합 + 시간순서**가 그림을 만든다 = **모자이크 이론**(SEC 인정 합법기법). 목표 = *정보 자체*가 아니라 *정보의 그림자*를 역추적.
>
> **시간 서명(temporal signature):** `t0 영향력행사 → t0-t1 정책진행 → t1 포지셔닝 → t2 결과 → t3 주가`. 한 종목/섹터에 이 발자국들이 *시간순 군집*하면 정보흐름 의심 플래그.

---

## 6층 한눈에

| # | 층 | 무엇을 (단위) | 소스 / 접근 | 키 | 갱신·지연 | 모자이크 단계 |
|---|---|---|---|---|---|---|
| ① | **로비** | 기업 분기 로비$·이슈·법안 | Senate LDA API `lda.senate.gov/api/v1/filings` | **불요 ★** | 분기, ~20일 후 | t0 영향력 |
| ② | **연방계약** | 기업 연방 수주$ (정책 결과) | USASpending `api.usaspending.gov` (POST) | **불요 ★** | 상시 | t2 결과 |
| ③ | **의원거래** | 누가·언제 매수/매도 | House FD.zip+PTR PDF / Senate eFD | **불요**(eFD=curl_cffi) | PTR 30~45일(중위 28) | t1 포지셔닝 |
| ④ | **위원회 관할** | 어느 의원이 어느 산업 감독 | congress-legislators `committee-membership-current.csv` | **불요 ★** | 임기내 고정(현재만) | t1 접근권 |
| ⑤ | **규제·입법** | 규칙·법안 타임라인 | Federal Register API `federalregister.gov/api` ★ · Congress.gov(키) · GovInfo | FR 불요 ★ / 법안 키 | FR 일간 | t0-t2 정책·결과 |
| ⑥ | **자금·외국** | 기업 PAC→의원 기부 / 외국 로비 | FEC `api.open.fec.gov`(DEMO_KEY) · FARA `efile.fara.gov` | DEMO/키 | 정기 신고 | t0 영향력 |

★ = 본 프로젝트에서 키 없이 작동 검증

---

## 층별 상세 — 접근·발견·함정

**① 로비 (LDA)** — *영향력 행사(t0)*
- 접근: `?client_name={기업}&filing_year={연}&page_size=25` → `income`(로비사 수임) 또는 `expenses`(인하우스) 합산. 페이지네이션.
- 발견: NVDA $0.64M→**$9.34M(14.6배, 2025)** 수출통제·관세 / INTC 세출로비=CHIPS·정부지분 / **FIX $0**(최대수익주인데 로비無=정책 아닌 AI). 
- **검증 결론:** 로비는 *주가 알파 아님*(종목 r=−0.26, 섹터내 헤비<라이트) — 가치-incumbent 프록시.
- 함정: client명 매칭(예 GOOG=Google LLC라 "Alphabet" 0으로 누락), 구간이 income/expenses 이원화.

**② 연방계약 (USASpending)** — *정책 결과($)(t2)*
- 접근: POST `/search/spending_by_award/` {recipient_search_text, award_type_codes, time_period}. recipient명 fuzzy(중복 합산·필터 필요).
- 역할: 로비·정책의 *현금 결과* — 방산·반도체·인프라 수주가 정책 후 늘었나.
- 함정: recipient명 fuzzy 매칭, 대기업 base-rate.

**③ 의원거래 (PTR + eFD)** — *포지셔닝(t1)*
- 하원: `disclosures-clerk.house.gov` FD.zip(XML 신고일)+ptr-pdfs(pdftotext). 상원: `efdsearch.senate.gov` — **Akamai WAF가 TLS차단 → curl_cffi `impersonate="chrome"` 필수**, agreement POST→report data→PTR HTML.
- 발견: 22,190건(2019~26). 시차 중위 28일. **따라 사도 SPY 미달(승률<50%)·지속성 0·net-flow 선행력 0.**
- 함정: 연례 *보유*신고(하원 스캔본)는 추출 불가 → 거래≠보유(GOP의 FIX/UTHR 누락 원인).

**④ 위원회 관할 (committee-membership)** — *접근권(t1)*
- 접근: `unitedstates.github.io/.../committee-membership-current.csv` (bioguide·name·committee). 산업→위원회 매핑(금융위→은행·증권, 국토안보→방산·정보 등).
- 발견: 관할위원 거래 ↔ 익년수익 **r=−0.04(무)** — Ziobrowski "위원회 정보채널" 가설, 본 표본(2019~26)선 불성립.
- 함정: **현재 명부만**(시변 아님) — 과거 의회 멤버십은 별도 확보 필요. 이름매칭.

**⑤ 규제·입법 (Federal Register / Congress.gov)** — *정책 자체(t0-t2)*
- 접근: FR `documents.json?conditions[type]=RULE&conditions[significant]=1&conditions[agencies][]={기관}&...` (오픈). 섹터→기관 매핑. 법안은 Congress.gov(키).
- 발견: 규제강도 원시 +0.24 → **섹터중립 시 −0.20 반전(순수 섹터 교란)**. 정책이벤트(CHIPS·관세)는 *다년 섹터효과 大*(반도체 +324%)이나 *동행≠선행*·통계 미확증.
- 함정: 규칙은 수혜/피해 사인 모호, 섹터정체성 프록시화.

**⑥ 자금·외국 (FEC / FARA)** — *영향력(t0)* — *미운영*
- 접근: FEC `api.open.fec.gov`(DEMO_KEY, rate제한) — 기업PAC→의원 기부. FARA — 외국 로비.
- 상태: PAC→의원→거래 매칭 체인이 복잡 → 본 프로젝트 미운영(다음 후보).

---

## 종합 — 모자이크가 답한 것 / 못 답한 것
- **층을 다 모아 검정해도(5층 패널 143obs, 다중검정·섹터중립·다년·이벤트·로비2단계) 거래 알파는 없다.** 유일 양성은 전부 *AI/섹터 교란*으로 환원.
- **모자이크의 진짜 가치 = 포렌식·거버넌스:** "기업 로비급증 + 관할위원 거래 + 직후 계약/규칙"의 시간순 군집 → *이해상충·정책노출 플래그*(감시·언론·컴플라이언스용). *알파 신호 아님.*
- **빠진 7번째 = 사적 정치정보(로비스트→기관, 정책을 *공개 전*에).** STOCK Act가 의원은 공시시키고 *정치정보 등록조항은 삭제* → **구조적으로 공개 발자국 밖.** 6층은 그 그림자만 비춘다.

## 운영 매핑 (이 프로젝트)
- 수집: `scripts/policy_mosaic.py`(①②) · `congress_ptr_pipeline.py`+`senate_ptr_pipeline.py`(③) · `mosaic_panel.py`(①~⑤ 통합) · `policy_radar_dashboard.py`(⑤ 규제 자동피드+플레이북).
- 대시보드: `dashboard/capitol_wave.html` "정책 플레이북 · 최근 규제이벤트" 섹션 = ⑤의 라이브 운영.
