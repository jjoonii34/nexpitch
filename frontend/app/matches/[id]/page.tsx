import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Suspense } from "react";
import Card from "@/components/Card";
import Loading from "@/components/Loading";
import SourceNotice from "@/components/SourceNotice";
import StandingsTable from "@/components/StandingsTable";
import FormRow from "@/components/match/FormRow";
import HeadToHeadCard from "@/components/match/HeadToHeadCard";
import Scoreboard from "@/components/match/Scoreboard";
import { formatKstTime, formatLongDate, toKstDate } from "@/lib/dates";
import { getHeadToHeadMatches, getMatch, getSeasonResults, getStandings } from "@/lib/football";
import { headToHead, recentForm } from "@/lib/insights";
import type { StandingRow } from "@/lib/types";

export const metadata = { title: "경기 상세 · nexpitch" };

/** 경기 상세. 껍데기는 미리 만들어 두고, 주소의 경기 id와 데이터는 요청이 올 때 채운다. */
export default function MatchPage({ params }: PageProps<"/matches/[id]">) {
  return (
    <Suspense fallback={<Loading title="경기 상세" />}>
      <MatchDetailView params={params} />
    </Suspense>
  );
}

/** 한 경기에 대해 스코어·경기 정보·순위 비교·최근 흐름·상대 전적을 보여준다. */
async function MatchDetailView({ params }: Pick<PageProps<"/matches/[id]">, "params">) {
  await connection(); // 요청 시점에 렌더링 (스코어가 빌드 때 값으로 굳지 않도록)
  const id = Number((await params).id);
  if (!Number.isInteger(id) || id <= 0) notFound(); // 주소에 숫자가 아닌 값이 오면 404

  // 네 요청은 서로 무관하므로 동시에 보낸다.
  const [match, season, h2hMatches, standings] = await Promise.all([
    getMatch(id),
    getSeasonResults(),
    getHeadToHeadMatches(id),
    getStandings(),
  ]);
  const m = match.data;
  if (!m) notFound();

  const sources = [match, season, h2hMatches, standings];
  const isSample = sources.some((s) => s.source === "sample");
  const error = sources.map((s) => s.error).find(Boolean);
  const day = toKstDate(new Date(m.kickoff));

  const homeForm = recentForm(season.data, m.home.id, m.kickoff);
  const awayForm = recentForm(season.data, m.away.id, m.kickoff);
  const h2h = headToHead(h2hMatches.data, m.home.id, m.away.id, m.id);
  // 두 팀의 순위 행만 골라 순위 순으로 (순위표에 없는 팀은 뺀다)
  const bothRows = standings.data
    .filter((r) => r.team.id === m.home.id || r.team.id === m.away.id)
    .sort((a: StandingRow, b: StandingRow) => a.position - b.position);

  return (
    <main>
      <header className="flex items-center gap-2 px-3 pb-2 pt-4">
        <Link href={`/?date=${day}`} aria-label="경기 목록으로" className="rounded-full px-2 py-1 text-lg text-muted hover:bg-surface-2">
          ←
        </Link>
        <p className="text-sm text-muted">
          {m.competition}
          {m.matchday ? ` · ${m.matchday}라운드` : ""}
        </p>
      </header>
      <SourceNotice source={isSample ? "sample" : "live"} error={error} />

      <Scoreboard match={m} />

      <Card title="경기 정보">
        <dl className="divide-y divide-line text-sm">
          <InfoRow label="일시" value={`${formatLongDate(day)} ${formatKstTime(m.kickoff)} (한국 시간)`} />
          {m.venue && <InfoRow label="경기장" value={m.venue} />}
          {m.referee && <InfoRow label="주심" value={m.referee} />}
        </dl>
      </Card>

      {bothRows.length > 0 && (
        <Card title="현재 순위">
          <StandingsTable rows={bothRows} compact />
        </Card>
      )}

      {(homeForm.length > 0 || awayForm.length > 0) && (
        <Card title="최근 리그 5경기" note="왼쪽이 가장 최근">
          <div className="divide-y divide-line">
            <FormRow team={m.home} form={homeForm} />
            <FormRow team={m.away} form={awayForm} />
          </div>
        </Card>
      )}

      {h2h.matches.length > 0 && <HeadToHeadCard h2h={h2h} home={m.home} away={m.away} />}

      <p className="px-4 pb-4 text-center text-xs text-muted">라인업·경기 스탯은 현재 데이터 제공 범위에 없어 표시하지 않습니다.</p>
    </main>
  );
}

/** 경기 정보의 한 줄 (항목 이름 — 값). */
function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 px-4 py-2.5">
      <dt className="shrink-0 text-muted">{label}</dt>
      <dd className="text-right">{value}</dd>
    </div>
  );
}
