import { connection } from "next/server";
import { Suspense } from "react";
import DateStrip from "@/components/DateStrip";
import MatchCard from "@/components/MatchCard";
import PageHeader from "@/components/PageHeader";
import SourceNotice from "@/components/SourceNotice";
import { formatLongDate, isValidYmd, toKstDate } from "@/lib/dates";
import { getMatches } from "@/lib/football";
import Loading from "@/components/Loading";
import { groupByCompetition } from "@/lib/mappers";

/** 경기 탭. 껍데기는 미리 만들어 두고, 날짜·경기 데이터는 요청이 올 때 Suspense 안에서 채운다. */
export default function MatchesPage({ searchParams }: PageProps<"/">) {
  return (
    <Suspense fallback={<Loading title="nexpitch" />}>
      <Matches searchParams={searchParams} />
    </Suspense>
  );
}

/** 날짜를 고르면 그날 경기를 리그별로 묶어 보여준다. */
async function Matches({ searchParams }: Pick<PageProps<"/">, "searchParams">) {
  await connection(); // 요청 시점에 렌더링한다 (오늘 날짜가 빌드 때 값으로 굳지 않도록)
  const { date } = await searchParams;
  const today = toKstDate(new Date());
  const selected = isValidYmd(date) ? date : today;

  const { data: matches, source, error } = await getMatches(selected);
  const groups = groupByCompetition(matches);

  return (
    <main>
      <PageHeader title="nexpitch" sub={formatLongDate(selected)} />
      <DateStrip selected={selected} today={today} />
      <SourceNotice source={source} error={error} />

      {groups.length === 0 ? (
        <p className="px-4 py-16 text-center text-sm text-muted">이 날은 경기가 없습니다.</p>
      ) : (
        groups.map((group) => (
          <section key={group.competition} className="mx-3 mb-3 overflow-hidden rounded-2xl bg-surface">
            <h2 className="border-b border-line px-4 py-2.5 text-sm font-bold">{group.competition}</h2>
            <ul className="divide-y divide-line">
              {group.matches.map((m) => (
                <MatchCard key={m.id} match={m} />
              ))}
            </ul>
          </section>
        ))
      )}
    </main>
  );
}
