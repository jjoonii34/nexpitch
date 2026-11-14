// 화면이 쓰는 우리만의 데이터 모양. 외부 API가 바뀌어도 화면 코드는 이 타입만 본다.

export type MatchStatus =
  | "scheduled" // 예정
  | "live" // 진행 중
  | "halftime" // 하프타임
  | "finished" // 종료
  | "postponed" // 연기
  | "cancelled"; // 취소·중단

export interface Team {
  id: number;
  name: string; // 짧은 이름 (예: Liverpool)
  tla: string; // 3글자 약어 (예: LIV)
  crest: string | null; // 엠블럼 이미지 주소. 없으면 약어로 대체 표시
}

export interface Match {
  id: number;
  competition: string; // 리그 이름 — 경기 탭에서 그룹 제목으로 쓴다
  matchday: number | null;
  kickoff: string; // ISO 8601 (UTC)
  status: MatchStatus;
  home: Team;
  away: Team;
  homeScore: number | null;
  awayScore: number | null;
}

export interface StandingRow {
  position: number;
  team: Team;
  played: number;
  won: number;
  draw: number;
  lost: number;
  goalDifference: number;
  points: number;
}

export interface Scorer {
  player: string;
  team: Team;
  goals: number;
  assists: number | null; // 무료 플랜에서 비어 올 수 있음
}

/** 데이터가 실제 API에서 왔는지, 키가 없어 샘플을 보여주는지 화면에 알려주기 위한 포장. */
export interface Sourced<T> {
  data: T;
  source: "live" | "sample";
  error?: string;
}
