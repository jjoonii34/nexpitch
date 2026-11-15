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

/** 경기 상세 화면용. 목록용 Match에 상세 호출에서만 오는 정보를 더한다. */
export interface MatchDetail extends Match {
  halfHome: number | null; // 전반 종료 시 홈 점수
  halfAway: number | null;
  referee: string | null; // 주심
  venue: string | null; // 경기장 (무료 플랜에서는 대부분 비어 옴)
}

export type Result = "W" | "D" | "L"; // 승 / 무 / 패

/** 한 팀 입장에서 본 지난 경기 한 건 (최근 흐름 표시용). */
export interface FormEntry {
  result: Result;
  match: Match;
}

/** 두 팀 맞대결 집계. home/away는 '지금 보고 있는 경기'의 홈·원정 팀 기준이다. */
export interface HeadToHead {
  homeWins: number;
  draws: number;
  awayWins: number;
  matches: Match[]; // 최신순
}

/** 뉴스 탭의 구단 선택 칸 하나. */
export interface Club {
  id: number;
  name: string;
}

/** 뉴스 카드 한 장. 제목·요약·바이라인은 가디언이 준 그대로 보여준다 (약관: 수정·번역 금지, ADR 0006). 본문은 원문 링크로. */
export interface NewsItem {
  id: number;
  title: string;
  summary: string;
  url: string; // 원문 주소
  author: string | null; // 바이라인이 없는 기사도 있다
  publishedAt: string; // ISO 8601 (UTC)
  source: string; // 매체 (예: guardian)
  clubs: string[]; // 이 기사에 연결된 구단 이름들
}
