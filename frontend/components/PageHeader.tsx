/** 각 탭 상단의 제목 줄. */
export default function PageHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <header className="flex items-baseline justify-between px-4 pb-2 pt-5">
      <h1 className="text-xl font-extrabold tracking-tight">{title}</h1>
      {sub && <span className="text-xs text-muted">{sub}</span>}
    </header>
  );
}
