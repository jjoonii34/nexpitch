import { formatGoalDifference } from "@/lib/labels";
import type { StandingRow } from "@/lib/types";
import Crest from "./Crest";

/**
 * 순위표. 리그 탭은 전체 열(경기·승·무·패·득실·승점), 경기 상세의 '현재 순위'는 compact로 경기·득실·승점만 보여준다.
 * 두 화면이 같은 표를 쓰도록 한 곳에 둔다.
 */
export default function StandingsTable({ rows, compact = false }: { rows: StandingRow[]; compact?: boolean }) {
  const th = "py-2 font-medium";
  return (
    <table className="w-full text-sm tabular-nums">
      <thead className="text-xs text-muted">
        <tr>
          <th scope="col" className={`w-9 pl-4 text-left ${th}`}>#</th>
          <th scope="col" className={`text-left ${th}`}>팀</th>
          <th scope="col" className={`w-10 text-center ${th}`}>경기</th>
          {!compact && <th scope="col" className={`w-7 text-center ${th}`}>승</th>}
          {!compact && <th scope="col" className={`w-7 text-center ${th}`}>무</th>}
          {!compact && <th scope="col" className={`w-7 text-center ${th}`}>패</th>}
          <th scope="col" className={`w-10 text-center ${th}`}>득실</th>
          <th scope="col" className={`w-12 pr-4 text-right ${th}`}>승점</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-line">
        {rows.map((row) => (
          <tr key={row.team.id}>
            <td className="py-2.5 pl-4 text-muted">{row.position}</td>
            <td className="py-2.5">
              <span className="flex items-center gap-2">
                <Crest team={row.team} size={20} />
                <span className="truncate">{row.team.name}</span>
              </span>
            </td>
            <td className="text-center">{row.played}</td>
            {!compact && <td className="text-center">{row.won}</td>}
            {!compact && <td className="text-center">{row.draw}</td>}
            {!compact && <td className="text-center">{row.lost}</td>}
            <td className="text-center">{formatGoalDifference(row.goalDifference)}</td>
            <td className="pr-4 text-right font-bold">{row.points}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
