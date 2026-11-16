import type { ReactNode } from "react";

/** 모든 탭이 쓰는 둥근 카드 묶음. 제목이 있으면 위에 줄로 붙이고, 오른쪽에 작은 메모를 달 수 있다. */
export default function Card({ title, note, children }: { title?: string; note?: string; children: ReactNode }) {
  return (
    <section className="mx-3 mb-3 overflow-hidden rounded-2xl bg-surface">
      {title && (
        <h2 className="flex items-baseline justify-between border-b border-line px-4 py-2.5 text-sm font-bold">
          {title}
          {note && <span className="text-xs font-normal text-muted">{note}</span>}
        </h2>
      )}
      {children}
    </section>
  );
}
