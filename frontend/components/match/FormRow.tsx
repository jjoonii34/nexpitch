import Link from "next/link";
import Crest from "@/components/Crest";
import { RESULT_LABEL } from "@/lib/labels";
import type { FormEntry, Result, Team } from "@/lib/types";

const RESULT_STYLE: Record<Result, string> = {
  W: "bg-win text-white",
  D: "bg-surface-2 text-muted",
  L: "bg-loss text-white",
};

/** 한 팀의 최근 경기 결과를 승·무·패 칩으로 보여준다. 칩을 누르면 그 경기 상세로 간다. */
export default function FormRow({ team, form }: { team: Team; form: FormEntry[] }) {
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
