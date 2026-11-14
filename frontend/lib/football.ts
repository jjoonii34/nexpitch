// 경기 데이터 창구. 화면은 이 파일의 함수 3개만 부른다.
// 서버 컴포넌트에서만 불리고, 키 이름에 NEXT_PUBLIC_ 접두사가 없어 API 키가 브라우저로 새지 않는다.

import { cacheLife } from "next/cache";
import { addDays, toKstDate } from "./dates";
import { mapMatch, mapScorers, mapStandings } from "./mappers";
import { sampleMatches, sampleScorers, sampleStandings } from "./sample";
import type { Match, Scorer, Sourced, StandingRow } from "./types";

const BASE = "https://api.football-data.org/v4";
const LEAGUE = "PL"; // v1은 프리미어리그만. 리그 확장은 v2 (docs/roadmap.md)

/** football-data.org를 호출한다. 'use cache'로 같은 주소의 응답을 seconds초 동안 재사용해 무료 한도(분당 10회, 확인 필요)를 지킨다. */
async function cachedGet(path: string, seconds: number): Promise<unknown> {
  "use cache";
  cacheLife({ stale: seconds, revalidate: seconds, expire: seconds * 10 });
  const res = await fetch(`${BASE}${path}`, {
    headers: { "X-Auth-Token": process.env.FOOTBALL_DATA_API_KEY ?? "" },
  });
  if (!res.ok) throw new Error(`football-data.org 응답 오류 (${res.status})`); // 오류는 캐시되지 않는다
  return res.json();
}

/** 키가 없으면 호출 자체를 하지 않는다 (샘플 데이터로 넘어가기 위한 신호). */
async function call(path: string, seconds: number): Promise<unknown> {
  if (!process.env.FOOTBALL_DATA_API_KEY) throw new Error("NO_KEY");
  return cachedGet(path, seconds);
}

/** 실패하면 샘플로 대체하고, 왜 대체했는지(키 없음/오류)를 함께 돌려준다. */
async function withFallback<T>(load: () => Promise<T>, fallback: T): Promise<Sourced<T>> {
  try {
    return { data: await load(), source: "live" };
  } catch (e) {
    const message = e instanceof Error ? e.message : "알 수 없는 오류";
    return { data: fallback, source: "sample", error: message === "NO_KEY" ? undefined : message };
  }
}

/** 한국 날짜 하루치 경기를 가져온다. 한국의 하루는 UTC로 이틀에 걸치므로 전날~당일을 조회한 뒤 한국 날짜로 거른다. */
export function getMatches(ymd: string): Promise<Sourced<Match[]>> {
  return withFallback(async () => {
    const json = (await call(
      `/competitions/${LEAGUE}/matches?dateFrom=${addDays(ymd, -1)}&dateTo=${ymd}`,
      60,
    )) as { matches?: unknown[] };
    return (json.matches ?? []).map(mapMatch).filter((m) => toKstDate(new Date(m.kickoff)) === ymd);
  }, sampleMatches(ymd));
}

/** 리그 순위표를 가져온다. */
export function getStandings(): Promise<Sourced<StandingRow[]>> {
  return withFallback(
    async () => mapStandings(await call(`/competitions/${LEAGUE}/standings`, 300)),
    sampleStandings,
  );
}

/** 득점 순위 상위 10명을 가져온다. */
export function getScorers(): Promise<Sourced<Scorer[]>> {
  return withFallback(
    async () => mapScorers(await call(`/competitions/${LEAGUE}/scorers?limit=10`, 300)),
    sampleScorers,
  );
}
