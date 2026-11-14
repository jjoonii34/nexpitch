import Link from "next/link";
import { formatKstTime } from "@/lib/dates";
import type { Match, MatchStatus } from "@/lib/types";
import Crest from "./Crest";

const STATUS_LABEL: Record<MatchStatus, string> = {
  scheduled: "예정",
  live: "진행 중",
  halftime: "하프타임",
  finished: "종료",
  postponed: "연기",
  cancelled: "취소",
};

/** 경기 한 줄: 왼쪽에 시간·상태, 가운데 두 팀, 오른쪽에 점수. 누르면 경기 상세로 간다. */
export default function MatchCard({ match }: { match: Match }) {
  const isLive = match.status === "live" || match.status === "halftime";
  const hasScore = match.homeScore !== null && match.awayScore !== null;
  const homeWon = match.status === "finished" && hasScore && match.homeScore! > match.awayScore!;
  const awayWon = match.status === "finished" && hasScore && match.awayScore! > match.homeScore!;

  return (
    <li>
      <Link href={`/matches/${match.id}`} className="flex items-center gap-3 px-4 py-3 hover:bg-surface-2">
        <div className="w-14 shrink-0 text-center text-xs">
          <div className="font-semibold tabular-nums">{formatKstTime(match.kickoff)}</div>
          <div className={isLive ? "font-bold text-live" : "text-muted"}>
            {isLive && <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-live align-middle" />}
            {STATUS_LABEL[match.status]}
          </div>
        </div>
        <div className="min-w-0 flex-1 space-y-1.5 border-l border-line pl-3">
          {(
            [
              [match.home, match.homeScore, homeWon, awayWon],
              [match.away, match.awayScore, awayWon, homeWon],
            ] as const
          ).map(([team, score, won, lost]) => (
            <div key={team.id} className={`flex items-center gap-2 ${lost ? "text-muted" : ""}`}>
              <Crest team={team} size={22} />
              <span className={`min-w-0 flex-1 truncate text-sm ${won ? "font-bold" : ""}`}>{team.name}</span>
              <span className={`w-5 text-right text-sm tabular-nums ${isLive ? "font-bold text-live" : won ? "font-bold" : ""}`}>
                {score ?? ""}
              </span>
            </div>
          ))}
        </div>
      </Link>
    </li>
  );
}
