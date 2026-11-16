import { connection } from "next/server";
import { Suspense } from "react";
import Card from "@/components/Card";
import Crest from "@/components/Crest";
import Loading from "@/components/Loading";
import PageHeader from "@/components/PageHeader";
import SourceNotice from "@/components/SourceNotice";
import StandingsTable from "@/components/StandingsTable";
import { getScorers, getStandings } from "@/lib/football";

export const metadata = { title: "리그 · nexpitch" };

/** 리그 탭. 껍데기는 미리 만들어 두고 순위 데이터는 요청이 올 때 채운다. */
export default function LeaguePage() {
  return (
    <Suspense fallback={<Loading title="리그" />}>
      <League />
    </Suspense>
  );
}

/** 순위표와 득점 순위. 두 요청은 서로 무관하므로 동시에 보낸다. */
async function League() {
  await connection(); // 빌드 때가 아니라 요청 시점에 렌더링 (빌드 때의 샘플/옛 순위가 굳지 않도록)
  const [standings, scorers] = await Promise.all([getStandings(), getScorers()]);
  const isSample = standings.source === "sample" || scorers.source === "sample";

  return (
    <main>
      <PageHeader title="리그" sub="Premier League" />
      <SourceNotice source={isSample ? "sample" : "live"} error={standings.error ?? scorers.error} />

      <Card title="순위">
        <StandingsTable rows={standings.data} />
      </Card>

      <Card title="득점 순위">
        <ol className="divide-y divide-line">
          {scorers.data.map((s, i) => (
            <li key={`${s.player}-${s.team.id}`} className="flex items-center gap-3 px-3 py-2.5 text-sm">
              <span className="w-5 text-muted tabular-nums">{i + 1}</span>
              <Crest team={s.team} size={20} />
              <span className="min-w-0 flex-1">
                <span className="block truncate">{s.player}</span>
                <span className="block truncate text-xs text-muted">{s.team.name}</span>
              </span>
              {s.assists !== null && <span className="text-xs text-muted tabular-nums">도움 {s.assists}</span>}
              <span className="w-8 text-right font-bold tabular-nums">{s.goals}</span>
            </li>
          ))}
        </ol>
      </Card>
    </main>
  );
}
