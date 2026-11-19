# ⚽ nexpitch

**한국어** · [日本語](README.ja.md)

프리미어리그 경기를 통계 모델과 LLM이 분석하고, **그 분석이 맞는지 직접 측정하는** AI 축구 앱.

[![Next.js](https://img.shields.io/badge/Next.js_16-000?logo=nextdotjs&logoColor=fff)](frontend)
[![Python](https://img.shields.io/badge/Python_3.13-3776AB?logo=python&logoColor=fff)](backend)
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch&logoColor=fff)](docs/adr/0014-선수-팀-임베딩-모델.md)
[![Gemini](https://img.shields.io/badge/Gemini-8E75B2?logo=googlegemini&logoColor=fff)](docs/adr/0009-LLM-분석가-같은-숫자-같은-지표.md)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=fff)](docs/adr/0003-뉴스-저장소는-Neon-PostgreSQL.md)
[![analysis-batch](https://github.com/jjoonii34/nexpitch/actions/workflows/analysis-batch.yml/badge.svg)](https://github.com/jjoonii34/nexpitch/actions/workflows/analysis-batch.yml)

**데모** → https://nexpitch-pi.vercel.app

## 핵심

- **같은 입력** — 통계 모델과 LLM에 같은 경기 전 숫자를 준다.
- **같은 채점** — 실제 결과로 Brier score를 재고, 차이가 우연인지 부트스트랩으로 판정한다.
- **기억 통제** — 팀 이름을 가린 입력과 비교해 LLM이 결과를 외운 것인지 확인한다.
- **가설은 LLM, 검증은 통계** — LLM의 가설을 과거 경기로 역검증한다.
- **직접 학습** — 직접 모은 선수 기록으로 임베딩 모델을 학습한다.

## 측정 결과

학습 2022·2023 시즌 → 평가 2024 시즌 380경기. Brier·로그 손실은 낮을수록 좋다.

| 모델 | Brier | 로그 손실 | 정확도 |
|---|---|---|---|
| 상수 (승·무·패 비율) | 0.6595 | 1.0860 | 40.8% |
| Elo | 0.6021 | 1.0048 | 53.2% |
| 특성 모델 | 0.6071 | 1.0540 | 51.8% |
| LLM (Gemini) | 0.5938 | 0.9945 | 51.6% |
| **LLM + Elo 평균** | **0.5937** | **0.9924** | 52.4% |

같은 경기끼리 짝지은 Brier 차 (95% 구간):

| 비교 | 차 | 95% 구간 | 판정 |
|---|---|---|---|
| LLM − Elo | −0.0083 | −0.0226 ~ +0.0057 | 차이 없음 |
| LLM+Elo − Elo | −0.0083 | −0.0155 ~ −0.0013 | **결합이 낫다** |
| 이름 가림 − 안 가림 (54경기) | +0.0047 | −0.0097 ~ +0.0187 | 기억 효과 근거 없음 |

프롬프트 버전 비교:

| 지표 | v1 (380경기) | v2 (97경기) |
|---|---|---|
| 검증 가능한 가설 | 0% | 100% |
| 서로 다른 가설 / 쓰인 특성 | — | 21개 / 1종류 |
| 비자명 가설 (Elo 단독 제외) | — | **0%** |
| 근거 숫자가 입력에 있는 비율 | 99% | 100% |

- 가설 97건 역검증: 근거 있음 83 · 표본 부족 12 · 근거 없음 2. 전부 Elo 단독 가설이라 성과로 보지 않는다.
- 전술 스탯의 반분 안정성(83경기): 패스 수 0.65 · 점유율 0.62 · xG 0.30.
- 전술 특성·임베딩 모델의 예측 성능은 **미측정** (데이터 수집 중, 11월 말 잠정 측정).

## 기능

| 영역 | 내용 |
|---|---|
| 경기·리그 | 날짜별 경기, 경기 상세, 순위표, 득점 순위 |
| 뉴스 | 20개 구단 가디언 기사 (원문 그대로, 최근 24시간) |
| 수집 | 라인업·팀 스탯·선수 스탯, 매일 자동 |
| 예측 | 상수·Elo·특성 모델, LLM 분석가, 결합 |
| 평가 | 시즌 단위 시간순 분리, 짝지은 부트스트랩, 프롬프트 평가 하네스, 가설 역검증 |
| 학습 | 선수·팀 임베딩 모델 (PyTorch) |

## 구조

```
Guardian ─────► 수집 배치 ──► Neon PostgreSQL ◄── 수집 배치 ◄── API-Football
                (GitHub Actions)     │
                                     ├──► 분석 (Elo · 로지스틱 · Gemini · PyTorch)
football-data.org ──► Next.js (Vercel) ◄── 사용자
```

- `frontend/` — Next.js 16. API 실패 시 샘플 데이터 + 표시 띠.
- `backend/` — Python. 수집기, 분석 모델, Alembic 마이그레이션.
- 테스트 — 프론트 16, 백엔드 76. 네트워크 없이 실행.
- 상주 서버 없음. 비용 0원.

## 데이터 소스

| 소스 | 용도 | 약관 제한 |
|---|---|---|
| football-data.org | 결과·순위 | 분당 10회 |
| The Guardian Open Platform | 뉴스 | 번역·가공 금지, 24시간 보관 ([ADR 0006](docs/adr/0006-가디언-약관-준수-번역과-LLM-가공-중지.md)) |
| API-Football | 라인업·스탯 | 하루 100회, 원본 재배포 금지 ([ADR 0007](docs/adr/0007-경기-분석-데이터는-API-Football-무료-플랜.md)) |
| 커뮤니티 사이트 | 수집하지 않음 | — |

## 로드맵

- [x] 경기·리그·뉴스 탭, 배포
- [x] 1단계 데이터 수집
- [x] 2단계 통계 기준선
- [x] 3단계 LLM 분석가
- [x] 4단계 가설 역검증
- [ ] 4.5단계 AI 분석가 고도화
  - [x] 평가 하네스
  - [x] 전술 특성 (코드)
  - [x] 임베딩 모델 (코드)
  - [ ] 프롬프트 v3
  - [ ] 사람 라벨 평가셋 100건
  - [ ] 실제 데이터 측정 (11월 말 잠정, 12월 말 최종)
- [ ] 5단계 분석 화면
- [ ] 6단계 이적 트래커 + 선수 영입 추천
- [ ] 팔로잉 탭

자세한 내용: [docs/roadmap.md](docs/roadmap.md)

## 실행

```bash
# 프론트
cd frontend
npm install && npm run dev
npm test

# 백엔드
cd backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
python -m alembic upgrade head
python -m app.analysis.run 2024           # 통계 모델 채점
python -m app.analysis.llm_run 2024       # LLM 분석가 실행·채점
python -m app.analysis.prompt_eval 2024   # 프롬프트 버전 비교
python -m app.analysis.tactical_run 2024  # 전술 특성 점검
pip install -r requirements-ml.txt
python -m app.analysis.embed_model 2024   # 임베딩 모델 학습
```

환경 변수: `frontend/.env.example`, `backend/.env.example` 참고.

## 문서

- 설계 결정 14건: [docs/adr/](docs/adr)
- 작업 기록: [docs/notes.md](docs/notes.md)

---

경기 데이터: football-data.org · API-Football &nbsp;|&nbsp; 뉴스: Powered by The Guardian
