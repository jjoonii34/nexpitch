// 실행: npm test  (Node 내장 테스트 러너 사용 — 테스트 라이브러리를 추가하지 않기 위해)
import assert from "node:assert/strict";
import { test } from "node:test";
import { addDays, isValidYmd, toKstDate } from "./dates.ts";
import { headToHead, recentForm, resultFor } from "./insights.ts";
import { formatGoalDifference, isLiveStatus } from "./labels.ts";
import { groupByCompetition, mapMatch, mapMatchDetail, mapStandings, mapStatus } from "./mappers.ts";

test("mapStatus: API 상태를 화면 상태로 줄인다", () => {
  assert.equal(mapStatus("TIMED"), "scheduled");
  assert.equal(mapStatus("IN_PLAY"), "live");
  assert.equal(mapStatus("PAUSED"), "halftime");
  assert.equal(mapStatus("FINISHED"), "finished");
  assert.equal(mapStatus("처음 보는 값"), "scheduled");
});

test("mapMatch: 점수가 없는 예정 경기도 깨지지 않는다", () => {
  const m = mapMatch({
    id: 7,
    utcDate: "2026-11-14T15:00:00Z",
    status: "TIMED",
    competition: { name: "Premier League" },
    homeTeam: { id: 64, name: "Liverpool FC", shortName: "Liverpool", tla: "LIV", crest: "x.png" },
    awayTeam: { id: 57, name: "Arsenal FC" },
    score: { fullTime: { home: null, away: null } },
  });
  assert.equal(m.home.name, "Liverpool");
  assert.equal(m.away.name, "Arsenal FC"); // shortName 없으면 name
  assert.equal(m.away.tla, "ARS"); // tla 없으면 이름 앞 3글자
  assert.equal(m.homeScore, null);
  assert.equal(m.status, "scheduled");
});

test("mapStandings: TOTAL 순위표만 사용한다", () => {
  const row = { position: 1, team: { id: 1, shortName: "A" }, playedGames: 1, won: 1, draw: 0, lost: 0, goalDifference: 2, points: 3 };
  const rows = mapStandings({
    standings: [
      { type: "HOME", table: [row, row] },
      { type: "TOTAL", table: [row] },
    ],
  });
  assert.equal(rows.length, 1);
  assert.equal(rows[0].points, 3);
  assert.deepEqual(mapStandings({}), []);
});

test("groupByCompetition: 리그별로 묶고 킥오프 순으로 정렬한다", () => {
  const mk = (id: number, competition: string, utcDate: string) =>
    mapMatch({ id, utcDate, status: "TIMED", competition: { name: competition }, homeTeam: {}, awayTeam: {} });
  const groups = groupByCompetition([
    mk(1, "PL", "2026-11-14T17:00:00Z"),
    mk(2, "PL", "2026-11-14T12:00:00Z"),
    mk(3, "UCL", "2026-11-14T20:00:00Z"),
  ]);
  assert.equal(groups.length, 2);
  assert.deepEqual(groups[0].matches.map((m) => m.id), [2, 1]);
});

test("날짜: UTC 밤 경기는 한국 날짜로 다음 날이다", () => {
  assert.equal(toKstDate(new Date("2026-11-14T20:00:00Z")), "2026-11-15");
  assert.equal(addDays("2026-11-30", 1), "2026-12-01");
  assert.equal(isValidYmd("2026-02-30"), false);
  assert.equal(isValidYmd("2026-11-14"), true);
});

/** 테스트용 끝난 경기 만들기: 홈팀 id, 원정팀 id, 점수, 날짜. */
const played = (id: number, home: number, away: number, hs: number, as: number, day: string) =>
  mapMatch({
    id,
    utcDate: `2026-${day}T15:00:00Z`,
    status: "FINISHED",
    homeTeam: { id: home, shortName: `T${home}` },
    awayTeam: { id: away, shortName: `T${away}` },
    score: { fullTime: { home: hs, away: as } },
  });

test("mapMatchDetail: 전반 스코어와 주심을 꺼낸다", () => {
  const d = mapMatchDetail({
    id: 1,
    utcDate: "2026-11-07T12:30:00Z",
    status: "FINISHED",
    homeTeam: {},
    awayTeam: {},
    score: { fullTime: { home: 1, away: 0 }, halfTime: { home: 0, away: 0 } },
    referees: [{ name: "보조", type: "ASSISTANT" }, { name: "주심", type: "REFEREE" }],
    venue: null,
  });
  assert.equal(d.halfHome, 0);
  assert.equal(d.referee, "주심");
  assert.equal(d.venue, null);
});

test("resultFor: 홈·원정 어느 쪽이든 그 팀 입장의 결과를 준다", () => {
  const m = played(1, 10, 20, 2, 1, "11-01");
  assert.equal(resultFor(m, 10), "W");
  assert.equal(resultFor(m, 20), "L");
  assert.equal(resultFor(m, 99), null); // 남의 경기
  assert.equal(resultFor(played(2, 10, 20, 1, 1, "11-02"), 20), "D");
});

test("recentForm: 기준 시각 이전 경기만, 최신순으로 count개", () => {
  const season = [
    played(1, 10, 20, 1, 0, "10-01"),
    played(2, 30, 10, 2, 2, "10-08"),
    played(3, 10, 40, 0, 3, "10-15"),
    played(4, 10, 50, 5, 0, "11-20"), // 기준 이후 → 제외
  ];
  const form = recentForm(season, 10, "2026-11-01T00:00:00Z", 2);
  assert.deepEqual(form.map((f) => f.result), ["L", "D"]);
});

test("headToHead: 홈·원정이 뒤바뀐 경기도 팀 기준으로 세고, 지금 경기는 뺀다", () => {
  const h2h = headToHead(
    [
      played(1, 10, 20, 1, 0, "11-07"), // 지금 보는 경기 → 제외
      played(2, 20, 10, 1, 1, "05-11"),
      played(3, 10, 20, 1, 2, "03-01"),
      played(4, 20, 10, 0, 3, "01-01"), // 원정에서 10번 팀이 이김
      played(5, 10, 30, 9, 0, "02-01"), // 다른 상대 → 제외
    ],
    10,
    20,
    1,
  );
  assert.deepEqual([h2h.homeWins, h2h.draws, h2h.awayWins], [1, 1, 1]);
  assert.deepEqual(h2h.matches.map((m) => m.id), [2, 3, 4]);
});

test("labels: 득실차 부호와 진행 중 판정", () => {
  assert.equal(formatGoalDifference(5), "+5");
  assert.equal(formatGoalDifference(0), "0");
  assert.equal(formatGoalDifference(-3), "-3");
  assert.equal(isLiveStatus("halftime"), true);
  assert.equal(isLiveStatus("finished"), false);
});
