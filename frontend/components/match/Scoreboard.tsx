import Crest from "@/components/Crest";
import { formatKstTime } from "@/lib/dates";
import { STATUS_LABEL, isLiveStatus } from "@/lib/labels";
import type { MatchDetail, Team } from "@/lib/types";

/** 경기 상세 맨 위: 두 팀 엠블럼 사이에 스코어(또는 킥오프 시각)·상태·전반 스코어. */
export default function Scoreboard({ match }: { match: MatchDetail }) {
  const live = isLiveStatus(match.status);
  const hasScore = match.homeScore !== null && match.awayScore !== null;
  return (
    <section className="mx-3 mb-3 rounded-2xl bg-surface px-3 py-6">
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <TeamBlock team={match.home} />
        <div className="text-center">
          {hasScore ? (
            <p className={`text-4xl font-extrabold tabular-nums ${live ? "text-live" : ""}`}>
              {match.homeScore} <span className="text-muted">-</span> {match.awayScore}
            </p>
          ) : (
            <p className="text-3xl font-extrabold tabular-nums">{formatKstTime(match.kickoff)}</p>
          )}
          <p className={`mt-1 text-xs ${live ? "font-bold text-live" : "text-muted"}`}>{STATUS_LABEL[match.status]}</p>
          {match.halfHome !== null && match.halfAway !== null && (
            <p className="mt-1 text-xs text-muted tabular-nums">
              전반 {match.halfHome} - {match.halfAway}
            </p>
          )}
        </div>
        <TeamBlock team={match.away} />
      </div>
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
