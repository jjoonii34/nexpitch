# nexpitch

프리미어리그 경기 결과·순위를 모바일 화면으로 보여주는 축구 앱. 이후 기자 티어가 붙은 이적·부상 뉴스 한국어 요약과, 그 요약 품질을 스스로 측정하는 기능으로 확장한다.

데모: https://nexpitch.vercel.app

## 현재 상태
- 경기 탭: 날짜별 경기, 리그별 그룹, 스코어·시간·상태
- 리그 탭: 순위표, 득점 순위
- 뉴스·팔로잉 탭: 준비 중

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

## 측정 결과
아직 측정한 수치 없음. (뉴스 요약 기능과 함께 추가 예정)

경기 데이터 제공: football-data.org
