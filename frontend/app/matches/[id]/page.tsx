import Link from "next/link";
import { notFound } from "next/navigation";
import { connection } from "next/server";
import { Suspense } from "react";
import Crest from "@/components/Crest";
import Loading from "@/components/Loading";
import SourceNotice from "@/components/SourceNotice";
import { formatKstFullDate, formatKstTime, formatLongDate, toKstDate } from "@/lib/dates";
import { getHeadToHeadMatches, getMatch, getSeasonResults, getStandings } from "@/lib/football";
import { headToHead, recentForm } from "@/lib/insights";
import type { FormEntry, Match, MatchStatus, Result, StandingRow, Team } from "@/lib/types";

export const metadata = { title: "경기 상세 · nexpitch" };

const STATUS_LABEL: Record<MatchStatus, string> = {
  scheduled: "예정",
  live: "진행 중",
  halftime: "하프타임",
  finished: "종료",
  postponed: "연기",
  cancelled: "취소",
};

const RESULT_LABEL: Record<Result, string> = { W: "승", D: "무", L: "패" };
const RESULT_STYLE: Record<Result, string> = {
  W: "bg-win text-white",
  D: "bg-surface-2 text-muted",
  L: "bg-loss text-white",
};

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

  const isSample = [match, season, h2hMatches, standings].some((s) => s.source === "sample");
  const error = match.error ?? season.error ?? h2hMatches.error ?? standings.error;
  const isLive = m.status === "live" || m.status === "halftime";
  const hasScore = m.homeScore !== null && m.awayScore !== null;
  const day = toKstDate(new Date(m.kickoff));

  const homeForm = recentForm(season.data, m.home.id, m.kickoff);
  const awayForm = recentForm(season.data, m.away.id, m.kickoff);
  const h2h = headToHead(h2hMatches.data, m.home.id, m.away.id, m.id);
  const rowOf = (team: Team) => standings.data.find((r) => r.team.id === team.id);

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

      {/* 스코어보드 */}
      <section className="mx-3 mb-3 rounded-2xl bg-surface px-3 py-6">
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
          <TeamBlock team={m.home} />
          <div className="text-center">
            {hasScore ? (
              <p className={`text-4xl font-extrabold tabular-nums ${isLive ? "text-live" : ""}`}>
                {m.homeScore} <span className="text-muted">-</span> {m.awayScore}
              </p>
            ) : (
              <p className="text-3xl font-extrabold tabular-nums">{formatKstTime(m.kickoff)}</p>
            )}
            <p className={`mt-1 text-xs ${isLive ? "font-bold text-live" : "text-muted"}`}>{STATUS_LABEL[m.status]}</p>
            {m.halfHome !== null && m.halfAway !== null && (
              <p className="mt-1 text-xs text-muted tabular-nums">
                전반 {m.halfHome} - {m.halfAway}
              </p>
            )}
          </div>
          <TeamBlock team={m.away} />
        </div>
      </section>

      <Card title="경기 정보">
        <dl className="divide-y divide-line text-sm">
          <InfoRow label="일시" value={`${formatLongDate(day)} ${formatKstTime(m.kickoff)} (한국 시간)`} />
          {m.venue && <InfoRow label="경기장" value={m.venue} />}
          {m.referee && <InfoRow label="주심" value={m.referee} />}
        </dl>
      </Card>

      {(rowOf(m.home) || rowOf(m.away)) && (
        <Card title="현재 순위">
          <table className="w-full text-sm tabular-nums">
            <thead className="text-xs text-muted">
              <tr>
                <th scope="col" className="w-9 py-2 pl-4 text-left font-medium">#</th>
                <th scope="col" className="py-2 text-left font-medium">팀</th>
                <th scope="col" className="w-10 py-2 text-center font-medium">경기</th>
                <th scope="col" className="w-10 py-2 text-center font-medium">득실</th>
                <th scope="col" className="w-12 py-2 pr-4 text-right font-medium">승점</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {[rowOf(m.home), rowOf(m.away)]
                .filter((r): r is StandingRow => Boolean(r))
                .sort((a, b) => a.position - b.position)
                .map((r) => (
                  <tr key={r.team.id}>
                    <td className="py-2.5 pl-4 text-muted">{r.position}</td>
                    <td className="py-2.5">
                      <span className="flex items-center gap-2">
                        <Crest team={r.team} size={20} />
                        <span className="truncate">{r.team.name}</span>
                      </span>
                    </td>
                    <td className="text-center">{r.played}</td>
                    <td className="text-center">{r.goalDifference > 0 ? `+${r.goalDifference}` : r.goalDifference}</td>
                    <td className="pr-4 text-right font-bold">{r.points}</td>
                  </tr>
                ))}
            </tbody>
          </table>
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

      {h2h.matches.length > 0 && (
        <Card title="상대 전적" note={`최근 ${h2h.matches.length}경기`}>
          <div className="grid grid-cols-3 border-b border-line py-3 text-center">
            <Tally value={h2h.homeWins} label={`${m.home.name} 승`} />
            <Tally value={h2h.draws} label="무승부" />
            <Tally value={h2h.awayWins} label={`${m.away.name} 승`} />
          </div>
          <ul className="divide-y divide-line">
            {h2h.matches.map((past) => (
              <PastMatchRow key={past.id} match={past} />
            ))}
          </ul>
        </Card>
      )}

      <p className="px-4 pb-4 text-center text-xs text-muted">라인업·경기 스탯은 현재 데이터 제공 범위에 없어 표시하지 않습니다.</p>
    </main>
  );
}

/** 제목이 달린 둥근 카드 묶음. */
function Card({ title, note, children }: { title: string; note?: string; children: React.ReactNode }) {
  return (
    <section className="mx-3 mb-3 overflow-hidden rounded-2xl bg-surface">
      <h2 className="flex items-baseline justify-between border-b border-line px-4 py-2.5 text-sm font-bold">
        {title}
        {note && <span className="text-xs font-normal text-muted">{note}</span>}
      </h2>
      {children}
    </section>
  );
}

/** 스코어보드 양옆의 팀 엠블럼과 이름. */
function TeamBlock({ team }: { team: Team }) {
  return (
    <div className="flex min-w-0 flex-col items-center gap-2 text-center">
      <Crest team={team} size={52} />
      <span className="w-full truncate text-sm font-semibold">{team.name}</span>
    </div>
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

/** 한 팀의 최근 경기 결과를 승·무·패 칩으로 보여준다. 칩을 누르면 그 경기 상세로 간다. */
function FormRow({ team, form }: { team: Team; form: FormEntry[] }) {
  return (
    <div className="flex items-center gap-2 px-4 py-2.5">
      <Crest team={team} size={20} />
      <span className="min-w-0 flex-1 truncate text-sm">{team.name}</span>
      <ol className="flex gap-1">
        {form.map(({ result, match }) => (
          <li key={match.id}>
            <Link
              href={`/matches/${match.id}`}
              title={`${match.home.name} ${match.homeScore}-${match.awayScore} ${match.away.name}`}
              className={`flex h-6 w-6 items-center justify-center rounded-md text-xs font-bold ${RESULT_STYLE[result]}`}
            >
              {RESULT_LABEL[result]}
            </Link>
          </li>
        ))}
        {form.length === 0 && <li className="text-xs text-muted">기록 없음</li>}
      </ol>
    </div>
  );
}

/** 상대 전적 집계의 숫자 한 칸. */
function Tally({ value, label }: { value: number; label: string }) {
  return (
    <div className="min-w-0 px-1">
      <p className="text-xl font-extrabold tabular-nums">{value}</p>
      <p className="truncate text-xs text-muted">{label}</p>
    </div>
  );
}

/** 과거 맞대결 한 줄: 날짜·대회와 스코어. */
function PastMatchRow({ match }: { match: Match }) {
  return (
    <li>
      <Link href={`/matches/${match.id}`} className="block px-4 py-2.5 hover:bg-surface-2">
        <p className="text-xs text-muted">
          {formatKstFullDate(match.kickoff)} · {match.competition}
        </p>
        <p className="mt-1 grid grid-cols-[1fr_auto_1fr] items-center gap-2 text-sm">
          <span className="truncate text-right">{match.home.name}</span>
          <span className="font-bold tabular-nums">
            {match.homeScore} - {match.awayScore}
          </span>
          <span className="truncate">{match.away.name}</span>
        </p>
      </Link>
    </li>
  );
}
