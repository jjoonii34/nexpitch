# ⚽ nexpitch

> **"LLM은 스포츠 데이터 분석가 역할을 할 수 있는가?"** — 프리미어리그 20개 구단의 경기 데이터 위에서 통계 모델과 LLM이 같은 문제(경기 결과 예측)를 풀게 하고, 누가 얼마나 맞히는지 앱이 스스로 측정하는 AI 기반 축구 앱

[![Next.js](https://img.shields.io/badge/Next.js_16-000?logo=nextdotjs&logoColor=fff)](frontend)
[![Python](https://img.shields.io/badge/Python_3.13-3776AB?logo=python&logoColor=fff)](backend)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL_(Neon)-4169E1?logo=postgresql&logoColor=fff)](docs/adr/0003-뉴스-저장소는-Neon-PostgreSQL.md)
[![Gemini](https://img.shields.io/badge/Gemini_flash--lite-8E75B2?logo=googlegemini&logoColor=fff)](docs/adr/0008-결과-예측-통계-기준선.md)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?logo=scikitlearn&logoColor=fff)](backend/app/analysis)
[![Vercel](https://img.shields.io/badge/Vercel-000?logo=vercel&logoColor=fff)](https://nexpitch-pi.vercel.app)
[![news-batch](https://github.com/jjoonii34/nexpitch/actions/workflows/news-batch.yml/badge.svg)](https://github.com/jjoonii34/nexpitch/actions/workflows/news-batch.yml)
[![analysis-batch](https://github.com/jjoonii34/nexpitch/actions/workflows/analysis-batch.yml/badge.svg)](https://github.com/jjoonii34/nexpitch/actions/workflows/analysis-batch.yml)

**데모** → https://nexpitch-pi.vercel.app · 

---

## 왜 만드나

축구 앱은 많지만 "AI 분석"은 대부분 그럴듯한 문장을 만들어 보여주는 데서 끝납니다. nexpitch는 반대로 갑니다.

1. **같은 숫자를 준다** — 두 팀의 Elo 레이팅, 최근 5경기 흐름, 휴식일, xG, 선발 변경 수를 통계 모델과 LLM에 **똑같이** 입력한다.
2. **같은 잣대로 잰다** — 승·무·패 확률을 Brier score·로그 손실로 채점해 **한 표에 나란히** 놓는다. 상수 모델(아무것도 모를 때)이 바닥이다.
3. **LLM의 기억을 걸러낸다** — LLM이 지난 시즌 결과를 외우고 있을 수 있으므로, **팀 이름을 가린 버전**과 비교해 "데이터로 추론한 것"과 "기억해 낸 것"을 분리한다.
4. **LLM은 가설 생성기** — "최적 11명" 같은 증명 불가한 주장 대신, LLM이 낸 선발·전술 가설을 과거 데이터로 **역검증(backtest)** 한다. 가설은 LLM, 검증은 통계.

이 네 가지가 "AI 기반"이라는 말을 **측정된 숫자**로 바꾸는 장치입니다.

## 지금 되는 것

| 탭 | 기능 | 데이터 |
|---|---|---|
| 경기 | 날짜별 경기, 리그별 그룹, 스코어·상태 → 경기 상세(순위 비교, 최근 5경기 흐름, 상대 전적) | football-data.org |
| 리그 | 순위표, 득점 순위 | football-data.org |
| 뉴스 | 20개 구단 기사 최신순, 구단 선택, 단어 검색 — 약관에 따라 **원문 그대로, 최근 24시간** | The Guardian Open Platform |
| (백엔드) | 경기별 라인업·포메이션·팀 스탯(xG)·선수 스탯 수집 — 2022~현재 시즌, 매일 자동 | API-Football |
| (백엔드) | 결과 예측 통계 기준선 3종 + 시즌 단위 시간순 평가 | 위 데이터 |

## 측정 결과

경기 결과(승·무·패) 예측 — 학습 2022·2023 시즌 → 평가 **2024 시즌 380경기** (2026-11-16, [ADR 0008](docs/adr/0008-결과-예측-통계-기준선.md)). 낮을수록 좋다.

| 모델 | Brier ↓ | 로그 손실 ↓ | 정확도 |
|---|---|---|---|
| 상수 (승·무·패 비율) | 0.6595 | 1.0860 | 40.8% |
| **Elo 차이만** | **0.6021** | **1.0048** | 53.2% |
| 특성 모델 (Elo+흐름+휴식+xG+선발 변경) | 0.6071 | 1.0540 | 51.8% |
| LLM 분석가 (Gemini) | *3단계 진행 중* | | |
| LLM + Elo 결합 | *3단계 진행 중* | | |
| LLM, 팀 이름 가림 | *3단계 진행 중* | | |

> xG·선발 변경 특성은 수집 중(하루 100회 한도, 약 38일)이라 특성 모델이 아직 Elo보다 낫지 않다. 데이터가 차는 대로 같은 명령으로 다시 재어 이 표를 갱신한다. 측정하지 않은 숫자는 적지 않는다.

## 구조

```
                 ┌─────────────────────────── 매일 GitHub Actions (상주 서버 없음) ───────────────────────────┐
                 │                                                                                           │
 The Guardian ───┼─► collect.py ──► Neon PostgreSQL ◄── analysis_collect.py ◄── API-Football                 │
 (원문, 24h)     │   (20개 구단)        ▲                 (라인업·xG·선수 스탯)                                  │
                 │                      │  읽기 (SQL)                                                         │
                 └──────────────────────┼─────────────────────────────────────────────────────────────────────┘
                                        │
 football-data.org ──(요청 시 직접)──► Next.js 16 (Vercel) ◄── 사용자 (모바일)
                                        ▲
                     app/analysis/ ─────┘  Elo · 로지스틱 · (3단계) Gemini 분석가 → predictions
```

- **frontend/** Next.js 16 (Cache Components). 화면은 외부 API의 모양을 모른다: `football.ts`(호출·캐시) → `mappers.ts`(순수 변환) → `types.ts` → 화면. 키가 없거나 실패하면 샘플 데이터를 보여주되 **"샘플 데이터입니다" 띠를 반드시** 띄운다.
- **backend/** Python. 수집기는 "소스 하나 = 클래스 하나" 규약, 네트워크 함수와 순수 변환 함수를 나눠 변환만 테스트한다. 분석 모듈은 **경기 전까지의 기록만**으로 특성을 만든다(정보 누출 금지).
- **테스트**: 프론트 16 (Node 내장 러너), 백엔드 44 (pytest, 메모리 SQLite·가짜 클라이언트). 전부 네트워크 없이 돈다.

## 데이터 소스와 약관 — 먼저 읽고, 조항을 인용한다

| 소스 | 쓰는 범위 | 약관에서 확인한 것 |
|---|---|---|
| football-data.org (무료) | 경기 결과·순위·득점 순위 | 분당 10회. 라인업·스탯 없음 |
| The Guardian Open Platform (개발자 키) | 기사 제목·요약·바이라인 **원문 그대로**, 24시간 보관, "Powered by The Guardian" 표기 | **번역·수정·LLM 가공·24시간 초과 보관 금지** → 만들었던 한국어 번역 기능을 2026-11-16에 걷어냈다 ([ADR 0006](docs/adr/0006-가디언-약관-준수-번역과-LLM-가공-중지.md)) |
| API-Football (무료) | 2022~현재 라인업·이벤트·팀 스탯·선수 스탯 | 하루 100·분당 10회. 원본 재판매 금지, 이미지는 식별 목적만(쓰지 않음) ([ADR 0007](docs/adr/0007-경기-분석-데이터는-API-Football-무료-플랜.md)) |
| 커뮤니티(에펨코리아·디시·X) | **긁지 않는다.** 링크만 | 자동 수집 금지 |

## 로드맵 (v1 · 2027-02)

- [x] 경기·리그 탭, 경기 상세, Vercel 배포
- [x] 뉴스 탭 (가디언 원문 피드, 구단 선택·검색, 하루 2회 자동 수집·24시간 정리)
- [x] **1단계** 분석 데이터 기반 — 테이블 8개, API-Football 수집기, 매일 배치 (데이터는 약 38일에 걸쳐 채워짐)
- [x] **2단계** 통계 기준선 — 상수·Elo·특성 로지스틱, 시즌 시간순 평가, 위 결과 표
- [ ] **3단계** LLM 분석가 — 같은 특성을 Gemini에 주고 예측·근거·선발 가설 JSON → 같은 지표로 비교, 팀 이름 가린 변형 실험
- [ ] **4단계** 가설 역검증 — LLM의 선발 가설을 과거 데이터로 backtest, 신뢰구간 표시. 북메이커 배당 벤치마크(약관 확인 중)
- [ ] **5단계** 화면 — 경기 상세 "데이터 분석" 탭: 예측 확률, 한국어 근거, 지난 예측 적중 기록. 라인업 표시
- [ ] **6단계** 이적 사가 트래커 — 루머를 직접 기록(기자·매체·선수·단계·원문 링크) → API-Football `transfers`로 확정 대조 → **기자별 적중률(=티어)** → 사가 신뢰도 %. 커뮤니티는 링크만
- [ ] 팔로잉 탭 (관심 구단·선수 → 피드 필터)

v2(2027 상반기): 5대 리그 확장, 선수 스탯 상세, Docker → k8s. v3: 한국인 선수 중심 기능. 자세한 것은 [docs/roadmap.md](docs/roadmap.md).

## 실행

```bash
# 프론트
cd frontend
cp .env.example .env.local        # FOOTBALL_DATA_API_KEY, DATABASE_URL (없으면 샘플 데이터로 동작)
npm install && npm run dev         # http://localhost:3000
npm test                           # 변환기·날짜·뉴스·라벨 테스트

# 백엔드
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # GUARDIAN_API_KEY, DATABASE_URL, API_FOOTBALL_KEY, GEMINI_API_KEY
python -m pytest                   # 44개, 네트워크 없음
python -m app.db                   # 없는 테이블 만들기
python -m app.collect              # 뉴스 수집 → DB,  python -m app.cleanup  # 24시간 정리
python -m app.analysis_collect 90  # 분석 데이터 수집 (하루 예산 안에서)
python -m app.analysis.run 2024    # 통계 기준선 평가 표 출력
```

## 설계 결정 (ADR)

| # | 결정 | 버린 대안 |
|---|---|---|
| [0001](docs/adr/0001-경기-데이터-API.md) | 경기 데이터는 football-data.org | TheSportsDB, API-Football(결과용으로는 한도 부족) |
| [0002](docs/adr/0002-첫-배포는-프론트-단독.md) | 첫 배포는 Next.js 단독, 백엔드 없이 | FastAPI 먼저 |
| [0003](docs/adr/0003-뉴스-저장소는-Neon-PostgreSQL.md) | 저장소는 Neon(호스팅 PostgreSQL) | Supabase, 로컬 Docker, SQLite |
| [0004](docs/adr/0004-뉴스-탭은-Next.js가-DB를-직접-읽는다.md) | 뉴스 탭은 Next.js가 DB를 직접 읽음 | FastAPI 경유 |
| [0005](docs/adr/0005-기사-번역은-Gemini-무료-티어-묶음-호출.md) | ~~기사 번역은 Gemini 묶음 호출~~ (폐기) | — |
| [0006](docs/adr/0006-가디언-약관-준수-번역과-LLM-가공-중지.md) | 가디언 기사는 원문 그대로 24시간만 | 약관 위반 상태 유지 (선택지 아님) |
| [0007](docs/adr/0007-경기-분석-데이터는-API-Football-무료-플랜.md) | 분석 데이터는 API-Football, 원본은 DB JSONB, 정규화 8테이블 | 유료 데이터, JSON만 저장 |
| [0008](docs/adr/0008-결과-예측-통계-기준선.md) | 기준선 = 상수·Elo·특성 로지스틱, 시즌 시간순 평가 | 포아송(백로그), 부스팅, 무작위 분리 |

## 배운 것 (요약 — 전체는 [docs/notes.md](docs/notes.md))

- **약관은 코드보다 먼저 읽는다.** 번역 기능을 다 만들고 나서 가디언 약관이 번역·LLM 가공을 금지한다는 걸 알았다. 하루 만에 걷어내고, 그 뒤로는 소스마다 조항을 ADR에 인용한다.
- **무료 한도가 설계를 정한다.** 모델 선택(flash-lite), 묶음 호출, 하루 90회 수집 배치, 38일짜리 적재 계획은 전부 한도 숫자에서 나왔다.
- **API 집계값을 믿지 않는다.** 상대 전적 집계가 틀려서 경기 목록에서 직접 셌다. 경기 데이터의 `"55%"`, `"2.43"`, `None`은 전부 다듬는 함수를 거친다.
- **배포가 안 바뀌면 연결된 레포 이름부터 본다.** Vercel이 다른 GitHub 계정의 옛 복사본을 보고 있었다. 깃 작성자 이메일도 다른 계정 것이었다.
- **Neon의 pooler 주소는 준비된 문장을 지원하지 않는다.** 같은 질의를 5번 넘게 보내면 연결이 끊긴다 → `prepare_threshold=None`.

---

경기 데이터 제공: football-data.org · API-Football &nbsp;|&nbsp; 뉴스: Powered by The Guardian (Open Platform, 원문 그대로 표시)
