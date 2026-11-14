// football-data.org 응답 → 우리 타입 변환기.
// 네트워크 없이 테스트할 수 있도록 순수 함수로만 구성한다 (입력이 같으면 출력이 같다).

import type { Match, MatchDetail, MatchStatus, Scorer, StandingRow, Team } from "./types";

/* eslint-disable @typescript-eslint/no-explicit-any -- 외부 API 응답은 형태를 보장받지 못하므로 any로 받고 여기서 검증한다 */

/** API의 상태 문자열을 화면에서 쓰는 6가지 상태로 줄인다. */
export function mapStatus(apiStatus: string): MatchStatus {
  switch (apiStatus) {
    case "IN_PLAY":
      return "live";
    case "PAUSED":
      return "halftime";
    case "FINISHED":
    case "AWARDED":
      return "finished";
    case "POSTPONED":
      return "postponed";
    case "SUSPENDED":
    case "CANCELLED":
      return "cancelled";
    default: // SCHEDULED, TIMED 및 모르는 값
      return "scheduled";
  }
}

/** 팀 정보를 변환한다. 짧은 이름이 없으면 전체 이름으로 대체한다. */
export function mapTeam(t: any): Team {
  const name: string = t?.shortName ?? t?.name ?? "미정";
  return {
    id: t?.id ?? 0,
    name,
    tla: t?.tla ?? name.slice(0, 3).toUpperCase(),
    crest: t?.crest ?? null,
  };
}

/** 경기 하나를 변환한다. */
export function mapMatch(m: any): Match {
  return {
    id: m.id,
    competition: m.competition?.name ?? "기타",
    matchday: m.matchday ?? null,
    kickoff: m.utcDate,
    status: mapStatus(m.status),
    home: mapTeam(m.homeTeam),
    away: mapTeam(m.awayTeam),
    homeScore: m.score?.fullTime?.home ?? null,
    awayScore: m.score?.fullTime?.away ?? null,
  };
}

/** 경기 상세 응답을 변환한다. 목록용 변환에 전반 스코어·주심·경기장을 더한다. */
export function mapMatchDetail(m: any): MatchDetail {
  const referee = (m.referees ?? []).find((r: any) => r.type === "REFEREE") ?? m.referees?.[0];
  return {
    ...mapMatch(m),
    halfHome: m.score?.halfTime?.home ?? null,
    halfAway: m.score?.halfTime?.away ?? null,
    referee: referee?.name ?? null,
    venue: m.venue ?? null,
  };
}

/** 순위 응답에서 전체(TOTAL) 순위표만 꺼내 변환한다 (홈/원정 순위표는 버린다). */
export function mapStandings(response: any): StandingRow[] {
  const total = (response?.standings ?? []).find((s: any) => s.type === "TOTAL");
  return (total?.table ?? []).map(
    (r: any): StandingRow => ({
      position: r.position,
      team: mapTeam(r.team),
      played: r.playedGames,
      won: r.won,
      draw: r.draw,
      lost: r.lost,
      goalDifference: r.goalDifference,
      points: r.points,
    }),
  );
}

/** 득점 순위 응답을 변환한다. */
export function mapScorers(response: any): Scorer[] {
  return (response?.scorers ?? []).map(
    (s: any): Scorer => ({
      player: s.player?.name ?? "이름 없음",
      team: mapTeam(s.team),
      goals: s.goals ?? 0,
      assists: s.assists ?? null,
    }),
  );
}

/** 경기 목록을 리그 이름별로 묶는다 (경기 탭의 '리그별 그룹'). 각 그룹은 킥오프 순으로 정렬한다. */
export function groupByCompetition(matches: Match[]): { competition: string; matches: Match[] }[] {
  const groups = new Map<string, Match[]>();
  for (const m of matches) {
    const list = groups.get(m.competition) ?? [];
    list.push(m);
    groups.set(m.competition, list);
  }
  return [...groups.entries()].map(([competition, list]) => ({
    competition,
    matches: [...list].sort((a, b) => a.kickoff.localeCompare(b.kickoff)),
  }));
}
