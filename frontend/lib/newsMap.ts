// 뉴스 탭의 순수 함수 모음: DB 행 → 우리 타입 변환, 주소창 값 검사, 검색어 다듬기.
// 네트워크·DB 없이 테스트할 수 있도록 여기에는 DB 호출을 두지 않는다 (호출은 news.ts).

import type { Club, NewsItem } from "./types";

/* eslint-disable @typescript-eslint/no-explicit-any -- DB에서 온 행은 형태를 보장받지 못하므로 any로 받고 여기서 검증한다 */

/** DB의 기사 행 하나를 뉴스 카드용 모양으로 바꾼다. */
export function mapNewsRow(row: any): NewsItem {
  return {
    id: Number(row.id),
    title: row.title ?? "",
    summary: row.body_or_summary ?? "",
    url: row.url,
    author: row.author || null,
    publishedAt: row.published_at,
    source: row.source ?? "",
    clubs: Array.isArray(row.clubs) ? row.clubs : [],
  };
}

/** DB의 구단 행 하나를 변환한다. */
export function mapClubRow(row: any): Club {
  return { id: Number(row.id), name: row.name };
}

/** 주소창의 club 값을 구단 번호로 바꾼다. 숫자가 아니거나 없으면 null (= 전체 구단). */
export function parseClubId(value: unknown): number | null {
  if (typeof value !== "string" || !/^\d{1,9}$/.test(value)) return null;
  const id = Number(value);
  return id > 0 ? id : null;
}

/** 주소창의 q 값을 검색어로 다듬는다. 앞뒤 공백을 떼고 너무 긴 입력은 자른다. 비면 null (= 검색 안 함). */
export function parseQuery(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const q = value.trim().slice(0, 50);
  return q === "" ? null : q;
}

/**
 * 검색어를 SQL의 '포함' 검색 무늬(%단어%)로 바꾼다.
 * %와 _는 SQL에서 '아무 글자'를 뜻하므로, 사용자가 입력한 것은 글자 그대로 찾도록 앞에 \를 붙인다.
 */
export function likePattern(q: string): string {
  return `%${q.replace(/[\\%_]/g, (ch) => `\\${ch}`)}%`;
}

/** 카드에 보여줄 구단 표시. 3곳까지는 이름을, 그보다 많으면(주말 종합 기사 등) 구단 수만 보여준다. */
export function clubsLabel(clubs: string[]): string {
  if (clubs.length === 0) return "";
  return clubs.length <= 3 ? clubs.join(" · ") : `${clubs.length}개 구단`;
}

/** 구단·검색어 선택을 뉴스 탭 주소로 만든다 (구단 칸과 검색 지우기 링크가 함께 쓴다). */
export function newsHref(clubId: number | null, q: string | null): string {
  const params = new URLSearchParams();
  if (clubId !== null) params.set("club", String(clubId));
  if (q !== null) params.set("q", q);
  const query = params.toString();
  return query ? `/news?${query}` : "/news";
}
