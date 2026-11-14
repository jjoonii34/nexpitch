// 날짜 계산 모음. 사용자는 한국 시간(KST)으로 보고, API는 UTC로 답하기 때문에 변환이 필요하다.

const KST = "Asia/Seoul";

/** Date를 한국 시간 기준 YYYY-MM-DD 문자열로 바꾼다 (경기를 '한국 날짜'로 묶기 위해). */
export function toKstDate(date: Date): string {
  // en-CA 로캘은 YYYY-MM-DD 형식으로 출력한다.
  return new Intl.DateTimeFormat("en-CA", { timeZone: KST }).format(date);
}

/** YYYY-MM-DD에 일수를 더하거나 뺀다 (날짜 스크롤, API 조회 범위 계산용). */
export function addDays(ymd: string, days: number): string {
  const d = new Date(`${ymd}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** 주소창의 date 값이 올바른 YYYY-MM-DD인지 검사한다 (잘못된 입력은 오늘로 대체). */
export function isValidYmd(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const d = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === value;
}

/** 킥오프 시각을 한국 시간 HH:MM으로 보여준다. */
export function formatKstTime(iso: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: KST,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(iso));
}

/** 날짜 스크롤 칸에 쓸 요일과 일(日)을 만든다. */
export function dayLabel(ymd: string): { weekday: string; day: string } {
  const d = new Date(`${ymd}T00:00:00Z`);
  const weekday = new Intl.DateTimeFormat("ko-KR", { timeZone: "UTC", weekday: "short" }).format(d);
  return { weekday, day: String(d.getUTCDate()) };
}

/** 화면 제목용 '11월 14일 (토)' 형식. */
export function formatLongDate(ymd: string): string {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "UTC",
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(new Date(`${ymd}T00:00:00Z`));
}

/** 지난 경기 날짜용 '2026년 4월 25일' 형식 (한국 시간 기준, 연도 포함). */
export function formatKstFullDate(iso: string): string {
  return new Intl.DateTimeFormat("ko-KR", { timeZone: KST, year: "numeric", month: "long", day: "numeric" }).format(new Date(iso));
}
