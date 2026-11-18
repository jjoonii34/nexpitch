# CLAUDE.md — nexpitch

이 파일은 Claude Code가 이 레포에서 일할 때 항상 먼저 읽는 지침이다. 아래 원칙과 맥락을 벗어나는 작업은 먼저 물어본다.

## 0. 가장 중요한 원칙 (하네스)

이 프로젝트는 **배우면서 만드는 포트폴리오**다. 코드를 대신 써도 되지만, 결과물은 반드시 소유자가 구조·기술 채택 근거·알고리즘을 **직접 설명할 수 있는 상태**여야 한다.

Claude Code가 지켜야 할 것:

1. **결정 전에 선택지와 근거를 먼저 보여준다.** 라이브러리, 폴더 구조, DB 스키마, 인프라를 정할 때는 2~3개 선택지 + 장단점 + 추천안을 짧게 제시하고, 승인 후 진행한다.
2. **큰 변경은 ADR로 남긴다.** `docs/adr/NNNN-제목.md`에 배경·선택지·결정·결과를 10줄 안팎으로 기록한다. 기술 스택 변경, 스키마 변경, 외부 API 채택이 대상이다.
3. **작업이 끝나면 "구술 요약"을 붙인다.** 한 번의 작업 단위가 끝날 때마다 3~5줄로 "무엇을 왜 이렇게 했는지"를 설명한다. 소유자가 이 요약만 읽고 남에게 설명할 수 있어야 한다.
4. **모르는 걸 숨기지 않는다.** 확신 없는 API 스펙, 바뀌었을 수 있는 무료 티어 조건은 "확인 필요"로 표시한다.
5. **한 번에 하나.** 파일 10개를 한꺼번에 만들지 않는다. 기능 하나 → 테스트 → 구술 요약 → 다음.
6. 소유자가 "직접 쓸게"라고 하면 코드 대신 **만들 것의 목록·시그니처·막힌 부분 해결책**만 준다.

## 1. 프로젝트 한 줄

프리미어리그 20개 구단 팬을 위한 **AI 기반** 축구 앱. 컨셉(2026-11-18): **원래 스포츠 데이터 분석가에게 맡겨야 할 수준의 분석 — 경기 전 승·무·패 확률, 근거, 검증 가능한 전술·선발 가설 — 을 통계 모델과 LLM이 대신 해 주고, 그 분석이 실제로 유의미한지(적중률·가설의 근거 유무)를 앱이 스스로 측정해 보여준다.** 경기 결과·순위는 FotMob 스타일 UI로 보여준다 (2026-11-16 방향 전환: 뉴스 요약 → 데이터 분석. 뉴스 탭은 가디언 원문 피드로 유지, ADR 0006).

- 레포: `jjoonii34/nexpitch` (배포: https://nexpitch-pi.vercel.app — `nexpitch.vercel.app`은 다른 Vercel 팀의 옛 프로젝트가 쥐고 있어 포기, 2026-11-16)
- 소유자: 융합소프트웨어학부 휴학생, 학부연구생(LLM 추천 연구). 개발 경험 적음 → 설명은 처음 보는 사람 기준으로.
- 목적: 포트폴리오 (대학원 + AI 엔지니어 취업). 비상업, 비용 0원 목표.
- 1차 사용자: 소유자 본인 (리버풀 팬).

## 2. 로드맵 (바꾸려면 먼저 물어볼 것)

| 버전 | 기한 | 범위 |
|---|---|---|
| v1 | 2027-02 | EPL 20개 구단 **경기 데이터 분석**: 라인업·이벤트·스탯 수집(2022~현재) → 결과 예측 통계 모델 → LLM 분석가(예측·근거·선발 가설) → 예측 적중률 측정·표시 + 경기 결과/순위 + 뉴스 원문 피드(가디언) |
| v2 | 2027 상반기 | 5대 리그 결과·순위·선수 스탯(득점·어시·반칙 등), Docker → k8s |
| v3 | 이후 | 한국인 선수 중심 기능 |

**지금은 v1만 한다.** v2·v3 기능 요청이 섞여 들어오면 `docs/roadmap.md` 백로그에 적고 멈춘다.

문서 표현 규칙: "한국인을 위한 FotMob" 같은 표현은 README·문서에 쓰지 않는다. FotMob은 UI 참고 대상일 뿐이다.

## 3. 기술 스택 (확정된 것)

| 영역 | 선택 | 메모 |
|---|---|---|
| 백엔드 | Python, FastAPI, PostgreSQL | 소유자가 뼈대 직접 작성 중 |
| 프론트 | Next.js | HTMX 대신 선택. 프로덕션 수준이 목표 |
| LLM | Gemini `gemini-3.5-flash-lite` 무료 티어 (배치) | 한도는 AI Studio에서 확인 (2026-11-14: 분당 15·하루 500). **가디언 기사에는 쓸 수 없다**(약관, ADR 0006). 용도: 경기 데이터 분석가 (2026-11-16) |
| 수집 | 가디언 Open Platform API(무료 개발자 키, 비상업, 초당 1·하루 500회) | **원문 그대로 24시간만 표시** (ADR 0006). BBC RSS는 약관상 불가(2026-11-16 확인). 새 소스는 약관 확인 → ADR 뒤에만 |
| 스케줄 | GitHub Actions cron (하루 2회 배치) | 서버 상주 프로세스 없음 |
| 배포 | Vercel(프론트), 백엔드는 무료 플랜 중 선택 예정 → ADR 필요 | |
| 컨테이너 | Docker (v1 후반), k8s는 v2 | |

경기 데이터 API는 football-data.org로 확정했다(ADR 0001). 분석용 라인업·이벤트·스탯은 API-Football 무료 플랜이 후보다(2026-11-16 확인: 2022~2024 시즌 조회 가능, 하루 100회) — **약관 확인 후 ADR 0007**. 정해지지 않은 것(백엔드 호스팅, DB, 인증 방식)은 **선택지 비교 → ADR → 진행** 순서를 지킨다.

## 4. 핵심 설계 규칙

### 4-1. 수집기(collector)
- 모든 소스는 같은 형태를 반환한다: `RawArticle(title, body_or_summary, url, author, published_at, source)`.
- 소스 추가 = 수집기 클래스 하나 추가. 기존 코드 수정 없이.
- 원문 전체를 재게시하지 않는다. 제목·링크·자체 요약만 저장·표시. 원문 링크 필수.
- API 원본 응답은 그대로 파일/테이블에 저장한다 (재실행 시 재호출 금지).

### 4-2. 기자 티어
- `journalists` 테이블: name, byline_name, x_handle, outlet, scope(national/club), club, tier_community(참고), tier_internal(초기 비움, 적중률로 채움).
- 티어 1 후보: 로마노, 온스테인, 폴 조이스, 제임스 피어스. 커뮤니티 티어표를 그대로 복사하지 않는다.
- 매 시즌 승격·강등으로 구단 목록이 바뀐다 → 구단은 하드코딩 금지, 테이블.

### 4-3. LLM 태깅·요약 (가디언 기사에는 적용 불가 — ADR 0006. 허용 소스가 생길 때까지 보류)
- 기사당 LLM 호출 1회, JSON 스키마 강제 출력: 카테고리(이적/부상/구단·오너/무관), 관련 구단·선수, 이적 단계(관심/협상/합의/메디컬/오피셜), 확실성(공식/보도/루머), 한국어 한 줄 요약.
- 프롬프트는 버전 문자열로 관리하고 결과에 버전을 함께 저장한다.
- 요약은 사용자별이 아니라 **이벤트(이적 건·이슈 건) 단위**로 만든다. 사용자 피드는 필터·정렬만.
- 콘텐츠 범위: 이적·출전·부상·전술·구단 경영. 선수·오너 사생활 가십은 제외.

### 4-4. 품질 측정 (2026-11-16 부활 — 대상이 '뉴스 요약'에서 '경기 예측'으로 바뀜)
- 정답 = 실제 경기 결과. 통계 모델·LLM·결합 세 가지의 승무패 확률을 같은 지표(Brier score 등)로 비교한다.
- LLM의 역할은 요약기가 아니라 **가설 생성기**(선발·전술 가설) → 통계로 역검증. "최적 11명" 같은 증명 불가한 주장은 하지 않는다.
- 구현: ADR 0008의 기준선 + README 결과 표. 지표·분리 방식은 그 ADR을 따른다.
- 아래는 원래 설계 메모(뉴스 요약 기준)이며 참고용이다.
- `eval/` 모듈은 다른 프로젝트로 추출될 예정 → 입력을 "추천 목록 + 정답 + 카탈로그 + 인기도"로만 받게 설계. 앱 내부 모델에 의존 금지.
- 측정 항목: 태깅 정확도(직접 라벨링한 테스트셋 50~100개), 요약 사실 오류율, 추천 혼잡도·인기 편향, 파싱 실패율, 비용·지연.
- 사용자 반응 버튼("정확해요/틀렸어요")은 사람 채점 데이터로 저장한다.
- 숫자가 나올 때마다 README 결과 표를 갱신한다.

### 4-5. FotMob 스타일 UI (참고 기준)
참고하는 것은 **정보 구조와 동선**이지 디자인 자산이 아니다. 로고·아이콘·색·문구를 복사하지 않는다.

- 하단 탭: 경기 / 뉴스 / 리그 / 팔로잉
- 경기 탭: 날짜 가로 스크롤, 리그별 그룹, 경기 카드(스코어·시간·상태)
- 경기 상세: 라인업·스탯·타임라인(v1은 결과·기본 스탯만)
- 리그 탭: 순위표, 득점·어시 순위
- 뉴스 탭: 이벤트 카드(카테고리 배지 + 기자 티어 배지 + 이적 단계) → 원문 링크
- 팔로잉: 관심 구단·선수 선택 → 피드 필터
- 모바일 퍼스트, 다크 모드 기본 지원

## 5. 레포 구조 (목표 형태 — 아직 없는 폴더도 포함)

```
nexpitch/
├── CLAUDE.md
├── README.md              # 결과 표·데모 링크·설계 결정 요약
├── docs/
│   ├── roadmap.md         # v1/v2/v3 + 백로그
│   ├── notes.md           # 작업 중 메모, 구술 요약 누적
│   └── adr/               # 0001-....md
├── backend/               # FastAPI
│   ├── app/
│   │   ├── collectors/    # 소스별 수집기
│   │   ├── llm/           # 프롬프트(버전), 어댑터, 태깅
│   │   ├── eval/          # 품질 측정 (보류, 독립 모듈)
│   │   ├── models/        # SQLAlchemy / 스키마
│   │   └── api/           # 라우터
│   └── tests/
├── frontend/              # Next.js
├── data/
│   ├── raw/               # 원본 응답 (git 제외)
│   └── testset/           # 직접 라벨링한 평가셋 (git 포함)
└── .github/workflows/     # 배치 cron, CI
```

## 6. 작업 방식

- **시작 전**: 관련 ADR·roadmap 확인. 범위 밖이면 멈추고 물어본다.
- **코드**: 함수 하나에 docstring 한 줄(왜 있는지). 타입 힌트 필수. 테스트는 지표 계산·파서·수집기 변환에 우선.
- **커밋**: 작게, 메시지는 한국어로 "무엇을 왜". 예: `feat(collector): 가디언 수집기 추가 — 바이라인 기반 기자 매칭 위해`
- **비밀**: `.env`, `data/raw/`는 커밋 금지. 키가 보이면 즉시 경고.
- **끝낼 때**: `docs/notes.md`에 구술 요약 추가 + 다음 할 일 1줄.

## 7. 금지 사항

- 소유자 승인 없이 유료 API·유료 플랜 사용
- 약관 위반 소지가 있는 스크래핑 (X 스크래퍼 등)
- **외부 콘텐츠를 저장·가공(번역·LLM·NLP)하기 전에 약관을 읽지 않는 것** — 소스마다 약관 조항을 ADR에 인용한다 (2026-11-16 가디언 건에서 배움)
- v2·v3 기능 선구현
- 근거 설명 없는 라이브러리 추가
- README에 측정하지 않은 성능 수치 작성

## 8. 구술 체크리스트 (소유자용)

작업이 끝나면 소유자가 아래를 말로 설명할 수 있는지 확인한다. 못 하면 Claude Code가 다시 설명한다.

- [ ] 이 기능이 왜 필요한가 (로드맵 어디에 해당하나)
- [ ] 왜 이 라이브러리/구조를 골랐나, 버린 대안은 무엇인가
- [ ] 데이터가 어디서 들어와 어디로 나가나
- [ ] 뭐가 틀릴 수 있고 어떻게 측정하나
- [ ] 비용이 드는 부분은 어디인가

---

# 현재 코드 안내

위 1~8번은 소유자가 정한 원칙이고, 아래는 지금 코드가 실제로 어떻게 생겼는지에 대한 안내다. 둘이 어긋나면 위 원칙이 우선이며, 어긋난 부분은 소유자에게 알린다.

## 지금 있는 것

nexpitch는 프리미어리그 경기 결과·순위·경기 상세를 모바일 화면으로 보여주는 앱이다. 이후 20개 구단 이적·부상 뉴스의 한국어 요약과 기자 티어로 확장한다. 배포 주소: https://nexpitch-pi.vercel.app

레포는 서로 독립된 두 부분으로 나뉜다. 공통 도구나 루트 `package.json`은 없다.

- `frontend/` — Next.js 16 앱. Vercel에 배포한다 (Root Directory = `frontend`, `main`에 push하면 자동 재배포). 서버 컴포넌트가 football-data.org와 뉴스 DB(Neon)를 직접 읽으며, 요청 경로에 백엔드 서버는 아직 없다 (ADR 0002, 0004).
- `backend/` — Python 뉴스 파이프라인. 첫 단위인 가디언 수집기만 있다. FastAPI 앱·DB·배포는 아직 없고, 저장이 필요한 기능과 함께 들어온다.

레포의 모든 글(코드 주석, 문서, 화면 문구, 커밋 메시지)은 한국어로 쓴다.

## 명령어

프론트 (`frontend/`에서 실행):

```bash
npm run dev      # http://localhost:3000 — API 키가 없어도 샘플 데이터로 동작
npm run build
npm run lint
npm test         # Node 내장 테스트 러너로 lib/*.test.ts 실행
node --test --test-name-pattern "recentForm" lib/mappers.test.ts   # 테스트 하나만
```

백엔드 (`backend/`에서 실행, 가상환경은 `backend/.venv`):

```bash
.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest                              # `python -m`으로 실행해야 `app`을 import할 수 있다
python -m pytest tests/test_guardian.py -k strip_html
python -m app.collectors.guardian             # 실제 수집. backend/.env에 GUARDIAN_API_KEY 필요
```

환경 파일: `frontend/.env.local`(`FOOTBALL_DATA_API_KEY`, `DATABASE_URL`), `backend/.env`(`GUARDIAN_API_KEY`, `DATABASE_URL`, `GEMINI_API_KEY`). 각각 커밋된 `.env.example`이 있다. 키 값은 커밋하지도 출력하지도 않는다.

## 프론트 구조

**먼저 `frontend/AGENTS.md`를 읽는다.** Next.js 16의 Cache Components 방식을 쓰며, 이전 버전과 다르다. Next API를 기억에 의존해 쓰지 말고 `frontend/node_modules/next/dist/docs/`를 확인한다.

데이터는 한 방향으로 흐르고, 화면은 외부 API의 모양을 모른다:

```
lib/football.ts  →  lib/mappers.ts  →  lib/types.ts  →  app/ + components/
(호출 + 캐시)        (순수 변환)         (우리 타입)       (서버 컴포넌트)
```

- football-data.org를 부르는 파일은 `lib/football.ts` 하나뿐이다. 화면은 이 파일의 `get…` 함수만 부르고, 모두 `Sourced<T>` = `{ data, source: "live" | "sample", error? }`를 돌려준다.
- **샘플 대체**: 키가 없거나 호출이 실패하면 `withFallback`이 `lib/sample.ts`의 데이터를 돌려준다. 모든 화면은 `source`·`error`를 `<SourceNotice>`에 넘겨 샘플이 진짜처럼 보이지 않게 한다. 화면을 추가할 때도 지킨다.
- **캐시 안에서는 오류를 값으로 돌려준다**: `cachedGet`(`"use cache"` + `cacheLife`)은 throw하지 않고 `{ ok: false, reason }`을 돌려준다. 캐시 함수 안에서 던진 오류는 배포 환경에서 내용이 가려지기 때문이다. 대가로 실패 결과도 같은 시간 동안 캐시된다.
- **호출 한도**는 무료 플랜 기준 분당 10회다. 캐시 시간: 경기 60초, 순위·득점 순위·시즌 결과 300초, 상대 전적 3600초. 새 엔드포인트를 부르기보다 이미 받은 데이터로 계산한다. `lib/insights.ts`는 시즌 전체 경기를 한 번 받아 최근 흐름을 계산하고, 상대 전적도 직접 센다 (API의 집계값이 틀렸음).
- **한국 시간과 UTC**: 사용자는 한국 날짜로 보고 API는 UTC로 답한다. `getMatches`는 전날~당일을 조회한 뒤 한국 날짜로 거른다. 날짜 계산은 직접 하지 말고 `lib/dates.ts`의 함수를 쓴다.
- **화면 작성 패턴**: 기본 export는 `<Suspense fallback={<Loading/>}>`로 감싼 동기 껍데기다. 그 안의 async 컴포넌트는 `await connection()`으로 시작하고(오늘 날짜와 스코어가 빌드 때 값으로 굳지 않도록), 이어서 `params`·`searchParams`를 await한다. 주소를 읽는 `BottomTabs`도 같은 이유로 레이아웃에서 Suspense로 감싼다. 감싸지 않으면 동적 경로가 빌드되지 않는다.
- v1은 프리미어리그만 다룬다 (`LEAGUE = "PL"`). 무료 플랜에는 라인업·이벤트·스탯이 없다.
- 공용 조각: 둥근 섹션은 `components/Card.tsx`, 순위표는 `components/StandingsTable.tsx`(경기 상세는 `compact`), 상태 문구·진행 중 판정·득실차 서식은 `lib/labels.ts`(순수 함수). 경기 상세의 조각은 `components/match/`. 같은 마크업을 두 번 쓰게 되면 여기로 뺀다.
- 스타일: Tailwind 4. 색은 `app/globals.css`에 정의한 의미 이름을 쓴다 (`bg-surface`, `text-muted`, `border-line`, `text-live`, `bg-win`, `bg-loss`). 본문은 가운데 정렬된 `max-w-xl` 폭이고 하단 탭은 고정이다.

- **뉴스 탭**(ADR 0004, 0006): `lib/news.ts`가 Neon을 직접 읽는 유일한 파일이다(`@neondatabase/serverless`, 5분 캐시, 읽기 전용). 가디언 약관대로 제목·요약·바이라인을 고치지 않고 보여주며, 페이지에 `GuardianAttribution`(로고·저작권)을 반드시 둔다. 화면은 `getClubs`·`getNews(clubId, q)`만 부르고 football.ts와 같은 `Sourced<T>`를 받는다. `DATABASE_URL`이 없으면 샘플 뉴스. SQL은 `backend/app/models/news.py`의 테이블 모양에 맞춰 쓰므로 테이블을 바꾸면 두 곳을 함께 고친다. 검색어 등 사용자 입력은 SQL에 이어 붙이지 않고 자리표시 값으로만 보낸다. 주소창 값 검사와 행 변환은 순수 모듈 `lib/newsMap.ts`에 있다.

**테스트 제약**: 테스트는 번들러 없이 Node가 TypeScript를 직접 실행한다. 그래서 테스트에서 닿는 파일은 실행 값을 import할 때 `.ts` 확장자를 붙여야 하고, `@/` 별칭과 `next/*` import를 쓸 수 없다. `mappers.ts`·`insights.ts`·`dates.ts`가 순수 함수이고 타입만 import하는 이유다. 테스트할 로직은 `lib/`의 순수 모듈에 두고, 네트워크 코드는 `football.ts`에만 둔다.

## 백엔드 구조

- 경로와 환경변수는 `app/settings.py`에서만 다룬다: `BACKEND_DIR`·`RAW_DIR`·`CLUBS_CSV`, `load_env()`, `require_env("이름")`. 다른 모듈은 `Path(__file__)`·`load_dotenv`·`os.environ`을 직접 쓰지 않는다.
- 테스트 공용 재료는 `tests/conftest.py`: 메모리 SQLite `session` fixture, `make_club`·`make_raw`·`make_article`, 고정 시각 `NOW`. 새 테스트는 이것부터 쓴다.
- `app/collectors/base.py`가 `RawArticle`(pydantic)과 `Collector` 규약(`source` 속성 + `collect() -> list[RawArticle]`)을 정의한다. 소스 추가는 이 규약을 따르는 클래스 하나를 더하는 것이고, 기존 코드는 고치지 않는다.
- 수집기마다 `fetch_raw`(네트워크 호출 + 원본 저장)와 모듈 함수 `parse`(원본 dict → `RawArticle` 목록, 네트워크 없음)를 나눈다. 테스트는 직접 만든 예시 응답으로 `parse`만 검증한다.
- 원본 응답은 `<레포 루트>/data/raw/<소스>/<YYYY-MM-DD>/<태그>.json`에 구단(태그)별로 저장한다 (git 제외). 같은 날 다시 실행하면 API를 부르지 않고 파일을 읽는다. 다시 받으려면 `force=True`.
- 배치: `python -m app.collect`가 프리미어리그 구단을 돌며 수집 → 저장한다(`app/collect.py`). 한 구단이 실패해도 계속하고 구단별 결과를 출력한다. 약 3분 걸린다. 이어서 `python -m app.cleanup`이 24시간 넘게 가디언 응답에 안 보인 기사를 지운다(약관, ADR 0006). 다시 본 기사는 `save_articles`가 `collected_at`을 갱신한다.
- 가디언은 API 키를 주소에 붙여 보낸다. 그래서 오류는 상태 코드만 알린다. httpx의 기본 오류나 주소를 그대로 내보내지 않는다.
- `parse`는 필수 값이 빠진 기사를 조용히 건너뛴다.
- 저장(ADR 0003): `app/models/news.py`에 테이블 3개(`clubs`, `articles`, `article_clubs`), `app/db.py`가 `DATABASE_URL`로 접속, `app/storage.py`의 `save_articles`가 `url` 기준으로 중복 없이 저장하고 구단과 연결한다. 테이블 구조는 **Alembic 마이그레이션으로만** 바꾼다(ADR 0011): 모델 수정 → `python -m alembic revision --autogenerate -m "설명"` → 생성 파일 읽고 손보기 → `python -m alembic upgrade head`. 배치 워크플로가 시작할 때 `upgrade head`를 돈다. `tests/test_migrations.py`가 마이그레이션 없이 모델만 바꾸면 실패한다. `alembic.ini`는 ASCII만(윈도우에서 한글이 깨짐). `create_tables`(create_all)는 테스트용.
- 구단 목록은 `<레포 루트>/data/clubs.csv`(이름, 가디언 태그)가 원본이다. `python -m app.clubs`가 `clubs` 테이블을 csv에 맞춘다(빠진 구단은 지우지 않고 `in_premier_league=False`). 가디언 태그는 이름에서 추측할 수 없으니 새 구단은 API로 확인한다.
- 번역(ADR 0005 → **폐기**, ADR 0006): `app/llm/translate.py`는 남아 있지만 배치·화면에서 쓰지 않는다. 가디언 기사는 LLM에 넣으면 안 된다. 원래 설명: `python -m app.llm.translate [최대 호출 수]`가 번역 없는 기사를 최신순으로 10건씩 묶어 Gemini(`gemini-3.5-flash-lite`, Interactions API + pydantic 스키마)에 보내고 `article_translations`에 프롬프트 버전과 함께 저장한다. 네트워크는 `translate_batch`에만 있고 나머지는 순수 함수라 가짜 번역 함수로 테스트한다. `PROMPT_VERSION`을 올리면 `frontend/lib/news.ts`의 같은 상수도 올린다. 무료 한도(분당 15·하루 500, 2026-11-14 확인)는 바뀔 수 있다.
- 분석 데이터(ADR 0007): `app/models/analysis.py` 테이블 8개(id는 API-Football id), `app/collectors/api_football.py`(네트워크는 `ApiFootballClient.get` 하나, 나머지 순수 변환), `app/analysis_store.py`(저장·덮어쓰기, 팀·선수 미리 읽기), `app/analysis_collect.py`(하루 예산 안에서 '아직 없는 것'부터, `python -m app.analysis_collect [호출 수]`). 무료 한도 하루 100·분당 10회, 호출 사이 7초. 원본은 `raw_responses`에.
- 분석 모델(ADR 0008): `app/analysis/` — `elo.py`, `dataset.py`(`load_matches` → `build_features`, 특성은 경기 전 기록만), `models.py`(constant·elo·features), `evaluate.py`(brier·log_loss·accuracy·time_split), `run.py`(`python -m app.analysis.run [평가 시즌]`). 모델 비교는 항상 같은 평가 시즌·같은 지표로. 숫자가 바뀌면 README 결과 표와 ADR 0008을 갱신한다.
- LLM 분석가(ADR 0009): `analysis/llm_analyst.py`(입력 글·확률 다듬기는 순수 함수, 네트워크는 `ask`/`ask_v2`), `predictions.py`(통계·LLM 예측을 `predictions`에 (경기, 모델, 버전)으로 저장), `llm_run.py`(`python -m app.analysis.llm_run [시즌] [최대 호출] [가림 경기 수] [v1|v2]`, 이미 있는 경기는 건너뛰어 이어서 실행 → 채점 표). **같은 실행을 두 개 띄우지 않는다** — 각자 시작할 때 '끝난 경기'를 읽어 서로 덮어쓰고 한도를 두 배로 쓴다. 모델 비교의 유의성은 `evaluate.paired_brier_diff`(같은 경기 짝 부트스트랩)로 본다.
- 가설 역검증(ADR 0010): 프롬프트 v2는 가설을 '특성 op 값이면 홈 승률 높다/낮다' 틀로 받아 `predictions.hypothesis_json`에 저장, `backtest.py`가 학습 시즌 경기에서 승률 차·부트스트랩 구간·표본 수로 판정(조건 양쪽 20경기 미만은 '표본 부족'), `backtest_run.py`가 `hypothesis_checks`에 저장. Neon의 `hypothesis_json` 열은 처음에 손 `ALTER TABLE`로 넣었고, Alembic 기준선(0001)에 포함한 뒤 Neon은 `stamp`로 맞췄다.
- 저장 테스트는 메모리 안의 SQLite로 돈다. 그래서 저장 코드에 PostgreSQL 전용 문법을 쓰지 않는다. `DATABASE_URL`에는 비밀번호가 있으니 출력하지 않는다.

## 작업 규칙 보충

위 6번 "작업 방식"에 더해, 지금까지의 커밋과 문서에서 굳어진 형식이다.

- **커밋**: `type(scope): 무엇 — 왜`. 예: `fix(frontend): API 실패 원인을 화면에 표시 — 배포 환경에서 오류 내용이 가려져 진단할 수 없어서`. 커밋과 PR에 `Co-Authored-By`나 "Generated with" 문구를 넣지 않는다.
- **`docs/notes.md`**: 날짜가 붙은 절을 추가하고 기존 소제목을 쓴다 — 무엇을 왜 / 틀릴 수 있는 것 / 비용 / 다음 할 일. 실제 API 응답으로 확인하지 못한 것은 그렇다고 적는다.
- **`docs/roadmap.md`**: "v1 진행 상황"의 항목을 날짜와 함께 체크하거나 추가한다.
- **아직 정하지 않은 것**(ADR 필요): 백엔드 호스팅, 경기 데이터 호출을 백엔드로 옮길지.
- 라이브러리를 추가할 때는 `requirements.txt`처럼 한 줄 주석으로 이유를 적는다.
