import Link from "next/link";
import { newsHref } from "@/lib/newsMap";
import type { Club } from "@/lib/types";

/** 구단 가로 스크롤. '전체' 또는 구단 하나를 고르면 ?club=로 이동한다. 검색어(q)는 그대로 유지한다. */
export default function ClubStrip({ clubs, selected, q }: { clubs: Club[]; selected: number | null; q: string | null }) {
  const chips: { id: number | null; name: string }[] = [{ id: null, name: "전체" }, ...clubs];

  return (
    <nav aria-label="구단 선택" className="no-scrollbar flex gap-1.5 overflow-x-auto px-3 py-2">
      {chips.map((chip) => {
        const active = chip.id === selected;
        return (
          <Link
            key={chip.id ?? "all"}
            href={newsHref(chip.id, q)}
            aria-current={active ? "true" : undefined}
            className={`shrink-0 rounded-full px-3 py-1.5 text-sm ${
              active ? "bg-accent font-bold text-white" : "bg-surface text-muted hover:bg-surface-2"
            }`}
          >
            {chip.name}
          </Link>
        );
      })}
    </nav>
  );
}
