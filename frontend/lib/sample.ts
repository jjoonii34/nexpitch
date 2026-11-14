// API 키가 없을 때 화면 모양을 확인하기 위한 샘플 데이터.
// 실제 결과가 아니며, 화면 상단에 "샘플 데이터" 안내가 반드시 함께 표시된다.

import type { Match, Scorer, StandingRow, Team } from "./types";

const team = (id: number, name: string, tla: string): Team => ({ id, name, tla, crest: null });

const LIV = team(1, "Liverpool", "LIV");
const ARS = team(2, "Arsenal", "ARS");
const MCI = team(3, "Man City", "MCI");
const CHE = team(4, "Chelsea", "CHE");
const TOT = team(5, "Tottenham", "TOT");
const MUN = team(6, "Man United", "MUN");

/** 고른 날짜에 맞춘 샘플 경기 3개를 만든다 (종료·진행 중·예정 상태를 하나씩 보여주기 위해). */
export function sampleMatches(ymd: string): Match[] {
  const at = (hhmm: string) => new Date(`${ymd}T${hhmm}:00+09:00`).toISOString();
  const base = { competition: "Premier League (샘플)", matchday: 1 };
  return [
    { ...base, id: 1, kickoff: at("20:30"), status: "finished", home: LIV, away: ARS, homeScore: 2, awayScore: 1 },
    { ...base, id: 2, kickoff: at("23:00"), status: "live", home: MCI, away: CHE, homeScore: 0, awayScore: 0 },
    { ...base, id: 3, kickoff: at("23:59"), status: "scheduled", home: TOT, away: MUN, homeScore: null, awayScore: null },
  ];
}

export const sampleStandings: StandingRow[] = [LIV, ARS, MCI, CHE, TOT, MUN].map((t, i) => ({
  position: i + 1,
  team: t,
  played: 10,
  won: 8 - i,
  draw: 1,
  lost: 1 + i,
  goalDifference: 12 - i * 4,
  points: (8 - i) * 3 + 1,
}));

export const sampleScorers: Scorer[] = [
  { player: "샘플 선수 A", team: LIV, goals: 9, assists: 4 },
  { player: "샘플 선수 B", team: MCI, goals: 8, assists: 1 },
  { player: "샘플 선수 C", team: ARS, goals: 6, assists: 5 },
];
