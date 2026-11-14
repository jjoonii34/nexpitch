// 경기 데이터 창구. 화면은 이 파일의 함수 3개만 부른다.
// 서버 컴포넌트에서만 불리고, 키 이름에 NEXT_PUBLIC_ 접두사가 없어 API 키가 브라우저로 새지 않는다.

import { cacheLife } from "next/cache";
import { addDays, toKstDate } from "./dates";
import { mapMatch, mapScorers, mapStandings } from "./mappers";
import { sampleMatches, sampleScorers, sampleStandings } from "./sample";
import type { Match, Scorer, Sourced, StandingRow } from "./types";

const BASE = "https://api.football-data.org/v4";
const LEAGUE = "PL"; // v1은 프리미어리그만. 리그 확장은 v2 (docs/roadmap.md)

type ApiResult = { ok: true; json: unknown } | { ok: false; reason: string };

/**
 * football-data.org를 호출한다. 'use cache'로 같은 주소의 응답을 seconds초 동안 재사용해 무료 한도(분당 10회, 확인 필요)를 지킨다.
 * 실패를 throw하지 않고 값으로 돌려준다 — 캐시 함수 안에서 던진 오류는 배포 환경에서 내용이 가려져 원인을 알 수 없기 때문.
 * (대가: 실패 결과도 seconds초 동안 캐시된다.)
 */
async function cachedGet(path: string, seconds: number): Promise<ApiResult> {
  "use cache";
  cacheLife({ stale: seconds, revalidate: seconds, expire: seconds * 10 });
  try {
    const res = await fetch(`${BASE}${path}`, {
      headers: { "X-Auth-Token": process.env.FOOTBALL_DATA_API_KEY ?? "" },
    });
    if (!res.ok) return { ok: false, reason: `football-data.org 응답 오류 (${res.status})` };
    return { ok: true, json: await res.json() };
  } catch (e) {
    return { ok: false, reason: `football-data.org 호출 실패 (${e instanceof Error ? e.message : "원인 불명"})` };
  }
}

/** 키를 검사한 뒤 호출한다. 키가 없으면 NO_KEY(샘플로 넘어가는 신호), 모양이 이상하면 그 사실을 알린다. */
async function call(path: string, seconds: number): Promise<unknown> {
  const key = process.env.FOOTBALL_DATA_API_KEY;
  if (!key) throw new Error("NO_KEY");
  // 키 자체는 절대 출력하지 않고 길이만 알려준다 (붙여넣기 실수 진단용).
  if (!/^[0-9a-f]{32}$/i.test(key)) {
    throw new Error(`API 키 형식이 올바르지 않습니다 (현재 ${key.length}자, 영문·숫자 32자여야 함. 공백·따옴표·'KEY=' 포함 여부 확인)`);
  }
  const result = await cachedGet(path, seconds);
  if (!result.ok) throw new Error(result.reason);
  return result.json;
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
