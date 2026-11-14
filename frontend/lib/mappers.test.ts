// 실행: npm test  (Node 내장 테스트 러너 사용 — 테스트 라이브러리를 추가하지 않기 위해)
import assert from "node:assert/strict";
import { test } from "node:test";
import { addDays, isValidYmd, toKstDate } from "./dates.ts";
import { groupByCompetition, mapMatch, mapStandings, mapStatus } from "./mappers.ts";

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
