"use client"; // 선택된 날짜 칸을 가운데로 스크롤하려면 브라우저 DOM이 필요하다.

import Link from "next/link";
import { useEffect, useRef } from "react";
import { addDays, dayLabel } from "@/lib/dates";

/** 날짜 가로 스크롤. 선택한 날 앞뒤 7일을 보여주고, 누르면 ?date=로 이동한다. */
export default function DateStrip({ selected, today }: { selected: string; today: string }) {
  const activeRef = useRef<HTMLAnchorElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ inline: "center", block: "nearest" });
  }, [selected]);

  const days = Array.from({ length: 15 }, (_, i) => addDays(selected, i - 7));

  return (
    <nav aria-label="날짜 선택" className="no-scrollbar flex gap-1 overflow-x-auto px-3 py-2">
      {days.map((ymd) => {
        const { weekday, day } = dayLabel(ymd);
        const active = ymd === selected;
        return (
          <Link
            key={ymd}
            ref={active ? activeRef : undefined}
            href={ymd === today ? "/" : `/?date=${ymd}`}
            aria-current={active ? "date" : undefined}
            className={`flex h-14 min-w-12 shrink-0 flex-col items-center justify-center rounded-xl text-xs ${
              active ? "bg-accent font-bold text-white" : "text-muted hover:bg-surface-2"
            }`}
          >
            <span>{ymd === today ? "오늘" : weekday}</span>
            <span className={`text-base ${active ? "" : "text-text"}`}>{day}</span>
          </Link>
        );
      })}
    </nav>
  );
}
