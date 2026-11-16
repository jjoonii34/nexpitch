import Link from "next/link";
import Card from "@/components/Card";
import { formatKstFullDate } from "@/lib/dates";
import type { HeadToHead, Match, Team } from "@/lib/types";

/** 상대 전적 카드: 집계 세 칸(홈 승·무·원정 승)과 과거 맞대결 목록. */
export default function HeadToHeadCard({ h2h, home, away }: { h2h: HeadToHead; home: Team; away: Team }) {
  return (
    <Card title="상대 전적" note={`최근 ${h2h.matches.length}경기`}>
      <div className="grid grid-cols-3 border-b border-line py-3 text-center">
        <Tally value={h2h.homeWins} label={`${home.name} 승`} />
        <Tally value={h2h.draws} label="무승부" />
        <Tally value={h2h.awayWins} label={`${away.name} 승`} />
      </div>
      <ul className="divide-y divide-line">
        {h2h.matches.map((past) => (
          <PastMatchRow key={past.id} match={past} />
        ))}
      </ul>
    </Card>
  );
}

/** 집계의 숫자 한 칸. */
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
