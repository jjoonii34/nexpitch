import Form from "next/form";
import Link from "next/link";
import { connection } from "next/server";
import { Suspense } from "react";
import Card from "@/components/Card";
import ClubStrip from "@/components/ClubStrip";
import GuardianAttribution from "@/components/GuardianAttribution";
import Loading from "@/components/Loading";
import NewsCard from "@/components/NewsCard";
import PageHeader from "@/components/PageHeader";
import SourceNotice from "@/components/SourceNotice";
import { getClubs, getNews } from "@/lib/news";
import { newsHref, parseClubId, parseQuery } from "@/lib/newsMap";

export const metadata = { title: "뉴스 · nexpitch" };

/** 뉴스 탭. 껍데기는 미리 만들어 두고, 구단·검색어와 기사는 요청이 올 때 Suspense 안에서 채운다. */
export default function NewsPage({ searchParams }: PageProps<"/news">) {
  return (
    <Suspense fallback={<Loading title="뉴스" />}>
      <News searchParams={searchParams} />
    </Suspense>
  );
}

/** 구단을 고르거나 단어로 검색해 기사를 최신순으로 본다. 기사는 backend 배치가 DB에 넣어 둔 것이고, 가디언 약관대로 원문 그대로 보여준다 (ADR 0006). */
async function News({ searchParams }: Pick<PageProps<"/news">, "searchParams">) {
  await connection(); // 요청 시점에 렌더링한다 (빌드 때의 기사 목록이 굳지 않도록)
  const params = await searchParams;
  const clubId = parseClubId(params.club);
  const q = parseQuery(params.q);

  // 두 조회는 서로 무관하므로 동시에 보낸다.
  const [clubs, news] = await Promise.all([getClubs(), getNews(clubId, q)]);
  const isSample = clubs.source === "sample" || news.source === "sample";
  const clubName = clubs.data.find((c) => c.id === clubId)?.name;

  return (
    <main>
      <PageHeader title="뉴스" sub={clubName ?? "프리미어리그 전체"} />

      <Form action="/news" className="mx-3 mb-1 flex gap-2">
        {/* 구단을 고른 상태에서 검색해도 구단 선택이 풀리지 않게 함께 보낸다 */}
        {clubId !== null && <input type="hidden" name="club" value={clubId} />}
        <input
          type="search"
          name="q"
          defaultValue={q ?? ""}
          maxLength={50}
          placeholder="제목·요약에서 검색 (영어, 예: injury, Salah)"
          aria-label="뉴스 검색"
          className="min-w-0 flex-1 rounded-xl border border-line bg-surface px-3 py-2 text-sm placeholder:text-muted focus:border-accent focus:outline-none"
        />
        <button type="submit" className="shrink-0 rounded-xl bg-accent px-4 text-sm font-bold text-white">
          검색
        </button>
      </Form>

      <ClubStrip clubs={clubs.data} selected={clubId} q={q} />
      <SourceNotice source={isSample ? "sample" : "live"} error={clubs.error ?? news.error} missing="DATABASE_URL" />
      <GuardianAttribution />

      {q !== null && (
        <p className="px-4 pb-2 text-xs text-muted">
          “{q}” 검색 결과 {news.data.length}건 ·{" "}
          <Link href={newsHref(clubId, null)} className="text-accent">
            검색 지우기
          </Link>
        </p>
      )}

      {news.data.length === 0 ? (
        <p className="px-4 py-16 text-center text-sm text-muted">조건에 맞는 뉴스가 없습니다.</p>
      ) : (
        <Card>
          <ul className="divide-y divide-line">
            {news.data.map((item) => (
              <NewsCard key={item.id} item={item} />
            ))}
          </ul>
        </Card>
      )}
    </main>
  );
}
