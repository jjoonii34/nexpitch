// 화면 여러 곳이 같이 쓰는 표시용 문구·서식. 숫자·상태를 글자로 바꾸는 순수 함수만 둔다 (테스트 가능).

import type { MatchStatus, Result } from "./types";

/** 경기 상태를 한국어로. 경기 카드와 경기 상세가 같은 문구를 쓴다. */
export const STATUS_LABEL: Record<MatchStatus, string> = {
  scheduled: "예정",
  live: "진행 중",
  halftime: "하프타임",
  finished: "종료",
  postponed: "연기",
  cancelled: "취소",
};

/** 승·무·패 한 글자. */
export const RESULT_LABEL: Record<Result, string> = { W: "승", D: "무", L: "패" };

/** 진행 중(전·후반, 하프타임)인지. 빨간 표시를 붙일지 정하는 기준. */
export function isLiveStatus(status: MatchStatus): boolean {
  return status === "live" || status === "halftime";
}

/** 득실차는 양수에 +를 붙여 보여준다 (0과 음수는 그대로). */
export function formatGoalDifference(value: number): string {
  return value > 0 ? `+${value}` : String(value);
}
