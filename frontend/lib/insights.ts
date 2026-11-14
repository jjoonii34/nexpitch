// 이미 받아 온 경기 목록에서 '최근 흐름'과 '상대 전적'을 계산한다.
// API가 주지 않는 정보를 직접 만들어 내는 곳이라, 네트워크 없는 순수 함수로 두고 테스트한다.

import type { FormEntry, HeadToHead, Match, Result } from "./types";

/** 한 팀 입장에서 그 경기가 승·무·패 중 무엇인지 판정한다. 끝나지 않았거나 그 팀 경기가 아니면 null. */
export function resultFor(match: Match, teamId: number): Result | null {
  if (match.status !== "finished" || match.homeScore === null || match.awayScore === null) return null;
  const isHome = match.home.id === teamId;
  if (!isHome && match.away.id !== teamId) return null;
  const mine = isHome ? match.homeScore : match.awayScore;
  const theirs = isHome ? match.awayScore : match.homeScore;
  return mine > theirs ? "W" : mine < theirs ? "L" : "D";
}

/** 기준 시각(before) 이전에 끝난 그 팀의 경기 중 최근 count개를 최신순으로 돌려준다. */
export function recentForm(matches: Match[], teamId: number, before: string, count = 5): FormEntry[] {
  const entries: FormEntry[] = [];
  const latestFirst = [...matches].sort((a, b) => b.kickoff.localeCompare(a.kickoff));
  for (const match of latestFirst) {
    if (match.kickoff >= before) continue; // 지금 보는 경기와 그 이후 경기는 제외
    const result = resultFor(match, teamId);
    if (result) entries.push({ result, match });
    if (entries.length === count) break;
  }
  return entries;
}

/** 맞대결 목록을 집계한다. 홈·원정이 뒤바뀐 과거 경기도 '팀' 기준으로 센다. excludeId는 지금 보는 경기. */
export function headToHead(matches: Match[], homeId: number, awayId: number, excludeId?: number): HeadToHead {
  const h2h: HeadToHead = { homeWins: 0, draws: 0, awayWins: 0, matches: [] };
  const latestFirst = [...matches].sort((a, b) => b.kickoff.localeCompare(a.kickoff));
  for (const match of latestFirst) {
    if (match.id === excludeId) continue;
    const result = resultFor(match, homeId);
    const involvesAway = match.home.id === awayId || match.away.id === awayId;
    if (!result || !involvesAway) continue;
    if (result === "W") h2h.homeWins++;
    else if (result === "L") h2h.awayWins++;
    else h2h.draws++;
    h2h.matches.push(match);
  }
  return h2h;
}
