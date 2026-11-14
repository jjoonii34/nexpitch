// 뉴스 데이터 창구. 화면은 DB를 직접 부르지 않고 이 파일의 get… 함수만 부른다 (ADR 0004).
// 서버 컴포넌트에서만 불리고, 변수 이름에 NEXT_PUBLIC_ 접두사가 없어 DB 주소가 브라우저로 새지 않는다.
// 기사를 넣는 쪽은 backend/의 배치이고, 여기서는 읽기만 한다.

import { neon } from "@neondatabase/serverless";
import { cacheLife } from "next/cache";
import { likePattern, mapClubRow, mapNewsRow } from "./newsMap";
import { sampleClubs, sampleNews } from "./sample";
import type { Club, NewsItem, Sourced } from "./types";

const PAGE_SIZE = 50; // 한 화면에 보여줄 최대 기사 수
const CACHE_SECONDS = 300; // 기사는 하루 2회만 들어오므로 5분 캐시로 충분하다
const PROMPT_VERSION = "v1"; // backend/app/llm/translate.py의 PROMPT_VERSION과 같아야 한다. 올리면 여기도 올린다.

type DbResult = { ok: true; rows: unknown[] } | { ok: false; reason: string };

/** 오류 문구에 DB 주소(비밀번호 포함)가 섞여 있으면 가린다. */
function safeReason(e: unknown): string {
  const message = e instanceof Error ? e.message : "원인 불명";
  return `뉴스 DB 조회 실패 (${message.replace(/postgres(ql)?:\/\/\S+/gi, "[주소 가림]")})`;
}

/**
 * 구단 목록을 읽는다. football.ts와 같은 이유로 실패를 throw하지 않고 값으로 돌려준다
 * (캐시 함수 안에서 던진 오류는 배포 환경에서 내용이 가려진다).
 */
async function cachedClubs(): Promise<DbResult> {
  "use cache";
  cacheLife({ stale: 3600, revalidate: 3600, expire: 36000 });
  try {
    const sql = neon(process.env.DATABASE_URL ?? "");
    return { ok: true, rows: await sql`SELECT id, name FROM clubs WHERE in_premier_league ORDER BY name` };
  } catch (e) {
    return { ok: false, reason: safeReason(e) };
  }
}

/**
 * 기사를 최신순으로 읽는다. clubId가 있으면 그 구단에 연결된 기사만, pattern이 있으면 제목·요약에 그 단어가 든 기사만.
 * 값은 SQL 문장에 이어 붙이지 않고 자리표시로 따로 보낸다 → 검색어에 무엇을 넣어도 SQL로 실행되지 않는다.
 */
async function cachedNews(clubId: number | null, pattern: string | null): Promise<DbResult> {
  "use cache";
  cacheLife({ stale: CACHE_SECONDS, revalidate: CACHE_SECONDS, expire: CACHE_SECONDS * 10 });
  try {
    const sql = neon(process.env.DATABASE_URL ?? "");
    const rows = await sql`
      SELECT a.id, a.title, a.body_or_summary, a.url, a.author, a.source,
             t.title_ko, t.summary_ko,
             to_char(a.published_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS published_at,
             (SELECT array_agg(c.name ORDER BY c.name)
                FROM article_clubs ac JOIN clubs c ON c.id = ac.club_id
               WHERE ac.article_id = a.id) AS clubs
        FROM articles a
        -- 한국어 번역은 따로 쌓인다(ADR 0005). 현재 프롬프트 버전의 것만 붙이고, 없으면 영어로 보여준다.
        LEFT JOIN article_translations t ON t.article_id = a.id AND t.prompt_version = ${PROMPT_VERSION}::text
       WHERE (${clubId}::int IS NULL
              OR EXISTS (SELECT 1 FROM article_clubs ac WHERE ac.article_id = a.id AND ac.club_id = ${clubId}::int))
         AND (${pattern}::text IS NULL
              OR a.title ILIKE ${pattern}::text OR a.body_or_summary ILIKE ${pattern}::text
              OR t.title_ko ILIKE ${pattern}::text OR t.summary_ko ILIKE ${pattern}::text)
       ORDER BY a.published_at DESC
       LIMIT ${PAGE_SIZE}`;
    return { ok: true, rows };
  } catch (e) {
    return { ok: false, reason: safeReason(e) };
  }
}

/** DB 주소가 없으면 샘플로, 조회가 실패하면 샘플과 함께 이유를 돌려준다. */
async function withFallback<T>(load: () => Promise<DbResult>, map: (rows: unknown[]) => T, fallback: T): Promise<Sourced<T>> {
  if (!process.env.DATABASE_URL) return { data: fallback, source: "sample" };
  const result = await load();
  if (!result.ok) return { data: fallback, source: "sample", error: result.reason };
  return { data: map(result.rows), source: "live" };
}

/** 뉴스 탭의 구단 선택 칸에 쓸 프리미어리그 구단 목록. */
export function getClubs(): Promise<Sourced<Club[]>> {
  return withFallback(cachedClubs, (rows) => rows.map(mapClubRow), sampleClubs);
}

/** 뉴스 목록. clubId가 null이면 전체 구단, q가 null이면 검색 없이 최신순. */
export function getNews(clubId: number | null, q: string | null): Promise<Sourced<NewsItem[]>> {
  return withFallback(
    () => cachedNews(clubId, q === null ? null : likePattern(q)),
    (rows) => rows.map(mapNewsRow),
    sampleNews,
  );
}
