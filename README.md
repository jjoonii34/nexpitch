# nexpitch

프리미어리그 경기 결과·순위를 모바일 화면으로 보여주는 축구 앱. 이후 프리미어리그 20개 구단의 이적·부상 뉴스를 기자 티어와 함께 한국어로 요약하는 기능으로 확장한다.

데모: https://nexpitch-pi.vercel.app (주소 `nexpitch.vercel.app` 이전 예정)

## 현재 상태
- 경기 탭: 날짜별 경기, 리그별 그룹, 스코어·시간·상태
- 리그 탭: 순위표, 득점 순위
- 경기 상세: 스코어, 경기 정보, 순위 비교, 최근 5경기 흐름, 상대 전적
- 뉴스 탭: 프리미어리그 20개 구단 기사(The Guardian, 최근 24시간) 최신순, 구단 선택, 단어 검색. 약관에 따라 원문 그대로 표시
- 팔로잉 탭: 준비 중

## 실행
```bash
cd frontend
cp .env.example .env.local   # FOOTBALL_DATA_API_KEY 입력 (없으면 샘플 데이터로 동작)
npm install
npm run dev                  # http://localhost:3000
npm test                     # 변환기·날짜 계산 테스트
```

## 구조
```
frontend/
  app/          화면 (경기 /, 리그 /league, 뉴스 /news, 팔로잉 /following)
  components/   경기 카드, 날짜 스크롤, 하단 탭 등
  lib/          football.ts(API 호출·캐시) → mappers.ts(변환) → types.ts
docs/
  adr/          설계 결정 기록
  roadmap.md    v1~v3 범위와 진행 상황
  notes.md      작업별 구술 요약
```

## 설계 결정
- [ADR 0001](docs/adr/0001-경기-데이터-API.md) 경기 데이터: football-data.org
- [ADR 0002](docs/adr/0002-첫-배포는-프론트-단독.md) 첫 배포는 Next.js 단독
- [ADR 0003](docs/adr/0003-뉴스-저장소는-Neon-PostgreSQL.md) 뉴스 저장소: Neon PostgreSQL
- [ADR 0004](docs/adr/0004-뉴스-탭은-Next.js가-DB를-직접-읽는다.md) 뉴스 탭은 Next.js가 DB를 직접 읽음
- [ADR 0005](docs/adr/0005-기사-번역은-Gemini-무료-티어-묶음-호출.md) 번역은 Gemini 무료 티어에 묶음 호출 (폐기)
- [ADR 0006](docs/adr/0006-가디언-약관-준수-번역과-LLM-가공-중지.md) 가디언 기사는 원문 그대로 24시간만, 번역·LLM 가공 중지

## 측정 결과
아직 측정한 수치 없음. (품질 측정 기능은 v1 범위에서 보류)

경기 데이터 제공: football-data.org · 뉴스: Powered by The Guardian (Open Platform, 원문 그대로 표시)
