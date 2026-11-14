import { connection } from "next/server";
import { Suspense } from "react";
import Crest from "@/components/Crest";
import Loading from "@/components/Loading";
import PageHeader from "@/components/PageHeader";
import SourceNotice from "@/components/SourceNotice";
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

      <section className="mx-3 mb-3 overflow-hidden rounded-2xl bg-surface">
        <h2 className="border-b border-line px-4 py-2.5 text-sm font-bold">순위</h2>
        <table className="w-full text-sm tabular-nums">
          <thead className="text-xs text-muted">
            <tr>
              <th scope="col" className="w-9 py-2 pl-3 text-left font-medium">#</th>
              <th scope="col" className="py-2 text-left font-medium">팀</th>
              <th scope="col" className="w-8 py-2 text-center font-medium">경기</th>
              <th scope="col" className="w-7 py-2 text-center font-medium">승</th>
              <th scope="col" className="w-7 py-2 text-center font-medium">무</th>
              <th scope="col" className="w-7 py-2 text-center font-medium">패</th>
              <th scope="col" className="w-10 py-2 text-center font-medium">득실</th>
              <th scope="col" className="w-10 py-2 pr-3 text-right font-medium">승점</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {standings.data.map((row) => (
              <tr key={row.team.id}>
                <td className="py-2.5 pl-3 text-muted">{row.position}</td>
                <td className="py-2.5">
                  <span className="flex items-center gap-2">
                    <Crest team={row.team} size={20} />
                    <span className="truncate">{row.team.name}</span>
                  </span>
                </td>
                <td className="text-center">{row.played}</td>
                <td className="text-center">{row.won}</td>
                <td className="text-center">{row.draw}</td>
                <td className="text-center">{row.lost}</td>
                <td className="text-center">{row.goalDifference > 0 ? `+${row.goalDifference}` : row.goalDifference}</td>
                <td className="pr-3 text-right font-bold">{row.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="mx-3 mb-3 overflow-hidden rounded-2xl bg-surface">
        <h2 className="border-b border-line px-4 py-2.5 text-sm font-bold">득점 순위</h2>
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
      </section>
    </main>
  );
}
